import io
import re
import base64
import logging
import PyPDF2
import lxml.html

from odoo import models

_logger = logging.getLogger(__name__)

EDGE_MM     = 5      # gap from every paper edge to nearest content
A4_WIDTH_PX = 794    # A4 at 96 dpi  (210 mm × 3.7795 px/mm)
MM_PER_PX   = 25.4 / 96


def _extract_div(html_str, class_name):
    """Return the first div containing class_name as an HTML string."""
    if not html_str:
        return ''
    try:
        s = html_str.decode('utf-8') if isinstance(html_str, bytes) else html_str
        tree = lxml.html.fromstring(s)
        nodes = tree.xpath(f"//div[contains(@class, '{class_name}')]")
        if nodes:
            return lxml.html.tostring(nodes[0], encoding='unicode')
    except Exception:
        _logger.warning('report_layout: could not extract .%s div', class_name)
    return ''


def _extract_head(html_str):
    """Return the raw content between <head>…</head>."""
    m = re.search(r'<head>(.*?)</head>', html_str, re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else ''


def _screenshot_div(browser, div_html, head_html, width_px=A4_WIDTH_PX):
    """
    Render div_html inside a full page (with Odoo CSS from head_html),
    screenshot exactly the rendered element, return (base64_str, height_mm).
    """
    render_html = (
        f'<!DOCTYPE html><html><head>{head_html}</head>'
        f'<body style="margin:0;padding:0;width:{width_px}px;">'
        f'{div_html}'
        f'</body></html>'
    )
    pg = browser.new_page()
    pg.set_viewport_size({'width': width_px, 'height': 600})
    pg.set_content(render_html, wait_until='networkidle')

    el = pg.query_selector('body > *:first-child')
    box = el.bounding_box() if el else None
    h_px = max(int(box['height']), 1) if box else 100

    img_bytes = pg.screenshot(
        clip={'x': 0, 'y': 0, 'width': width_px, 'height': h_px}
    )
    pg.close()
    return base64.b64encode(img_bytes).decode(), h_px * MM_PER_PX


def _merge_pdfs(pdf_list):
    writer = PyPDF2.PdfWriter()
    for pdf_bytes in pdf_list:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _run_wkhtmltopdf(
            self,
            bodies,
            report_ref=False,
            header=None,
            footer=None,
            landscape=False,
            specific_paperformat_args=None,
            set_viewport_size=False):
        """
        Playwright/Chromium PDF renderer — replaces wkhtmltopdf.

        Header and footer are screenshotted as PNG images and embedded as data
        URIs in Playwright's header_template / footer_template so they repeat
        on EVERY page.  --disable-web-security allows Lato and other web fonts
        served from http://localhost to load when content is set via set_content().
        """
        from playwright.sync_api import sync_playwright

        paperformat_id = (
            self._get_report(report_ref).get_paperformat()
            if report_ref else self.get_paperformat()
        )

        fmt = 'A4'
        if paperformat_id and paperformat_id.format and paperformat_id.format != 'custom':
            fmt = paperformat_id.format

        header_div = _extract_div(header, 'header')

        # CSS that Odoo adds to body (.o_body_html / .o_body_pdf.o_css_margins = 11mm
        # padding on all sides in PDF mode, Bootstrap .container max-width) must be
        # neutralised so our EDGE_MM is the only gap.
        body_reset = (
            '<style>'
            '.o_body_html,'
            '.o_body_pdf,'
            '.o_body_pdf.o_css_margins{'
            'padding:0!important;margin:0!important;}'
            '.container,.container-fluid{padding-left:0!important;padding-right:0!important;'
            'max-width:100%!important;margin:0!important;}'
            '</style>'
        )

        all_pdfs = []

        with sync_playwright() as p:
            # --disable-web-security: allows cross-origin font/CSS requests
            # from null-origin (set_content) to http://localhost:8069
            browser = p.chromium.launch(args=['--disable-web-security'])

            # Extract Odoo CSS head from the first body for screenshot rendering
            first_body = bodies[0]
            first_body_str = first_body.decode('utf-8') if isinstance(first_body, bytes) else first_body
            head_html = _extract_head(first_body_str)

            # --- Screenshot header → PNG data URI ---
            header_template = '<span></span>'   # Playwright requires non-empty string
            margin_top_mm = EDGE_MM
            if header_div:
                hb64, h_mm = _screenshot_div(browser, header_div, head_html)
                # +5 mm safety buffer: the PDF renderer scales the image slightly
                # differently from the screenshot, so add headroom to prevent
                # the header from overlapping body content on page 2+.
                margin_top_mm = EDGE_MM + h_mm + 5
                header_template = (
                    f'<div style="width:100%;padding:{EDGE_MM}mm {EDGE_MM}mm 0 {EDGE_MM}mm;'
                    f'box-sizing:border-box;">'
                    f'<img src="data:image/png;base64,{hb64}"'
                    f' style="width:100%;display:block;"/>'
                    f'</div>'
                )

            # --- Footer: HR line + centred page number (pure HTML, no screenshot) ---
            # EDGE_MM top-padding pushes content away from the paper edge.
            # Total space reserved = EDGE_MM + ~8 mm for line + text.
            margin_bottom_mm = EDGE_MM + 8
            footer_template = (
                '<style>'
                '* { -webkit-print-color-adjust: exact !important;'
                '    color: #000 !important; }'
                'body { margin:0; padding:0; }'
                '</style>'
                f'<div style="width:100%;padding-top:{EDGE_MM}mm;'
                f'box-sizing:border-box;font-family:Arial,sans-serif;font-size:8pt;">'
                '<hr style="border:none;border-top:1px solid #000;margin:0 0 2mm 0;"/>'
                '<p style="margin:0;text-align:center;color:#000;">'
                'Page <span class="pageNumber" style="color:#000;"></span>'
                ' / <span class="totalPages" style="color:#000;"></span>'
                '</p>'
                '</div>'
            )

            margin = {
                'top':    f'{margin_top_mm:.1f}mm',
                'bottom': f'{margin_bottom_mm:.1f}mm',
                'left':   '0mm',
                'right':  '0mm',
            }

            for body in bodies:
                body_str = body.decode('utf-8') if isinstance(body, bytes) else body
                # Inject CSS reset so Odoo body padding doesn't add extra spacing
                body_str = body_str.replace('</head>', body_reset + '\n</head>', 1)

                pg = browser.new_page()
                try:
                    pg.set_content(body_str, wait_until='networkidle')
                    pdf_bytes = pg.pdf(
                        format=fmt,
                        landscape=bool(landscape),
                        display_header_footer=True,
                        header_template=header_template,
                        footer_template=footer_template,
                        margin=margin,
                        print_background=True,
                    )
                    all_pdfs.append(pdf_bytes)
                finally:
                    pg.close()

            browser.close()

        if len(all_pdfs) == 1:
            return all_pdfs[0]

        return _merge_pdfs(all_pdfs)
