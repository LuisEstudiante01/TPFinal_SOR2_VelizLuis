#!/usr/bin/env python3
"""Academic styling for the report (R11: Calibri 11, A4, numbered pages).

Two modes, both edit a .docx in place:

  style_reference.py reference <reference.docx>
      Takes pandoc's default reference.docx and sets: A4 page, 2.5 cm margins,
      footer with a centered PAGE field (titlePg => none on the cover), body /
      heading / table / caption / TOC styles. Named styles only; the page
      layout lives in the sectPr (pandoc copies it into the output).

  style_reference.py post <report.docx>
      Runs after pandoc. Pipe tables come out with equal fixed column widths,
      which wraps words mid-word. This recomputes each table's column widths
      from its content (never narrower than the longest word; font 10/8/7.5 pt for <8/8-9/10+ columns), makes the table
      100% of the text width, and switches table paragraphs from "Compact" to
      the "TableText" style (10 pt). The two-column cover table (first one, no
      header row) gets fixed 2400/4600 widths and is centered.
"""
import re
import shutil
import sys
import tempfile
import zipfile

FONT = ('<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" '
        'w:eastAsia="Calibri" w:cs="Calibri"/>')
INK = "1F1F1F"
HEAD = "2F4A7A"  # soft dark blue for section headings
TH_FILL = "C6D4EE"  # soft pastel blue for table header rows
PAGE_W, PAGE_H, MARGIN = 11906, 16838, 1418
TEXT_W = PAGE_W - 2 * MARGIN  # 9070 twips
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
BORDER = 'w:val="single" w:sz="4" w:space="0" w:color="808080"'


def rewrite(path, fn):
    """Apply fn(name, bytes) -> bytes | None to each part; extra=dict adds parts."""
    tmp = tempfile.mktemp(suffix=".docx")
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            dst.writestr(item, fn(item.filename, src.read(item.filename)))
        for name, data in fn.extra.items():
            dst.writestr(name, data)
    shutil.move(tmp, path)


def set_style(xml, style_id, new):
    pat = re.compile(r'<w:style [^>]*w:styleId="%s".*?</w:style>' % style_id, re.S)
    if pat.search(xml):
        return pat.sub(lambda m: new, xml, count=1)
    return xml.replace("</w:styles>", new + "</w:styles>")


def pstyle(sid, name, based, ppr="", rpr="", extra="", custom=False):
    return (f'<w:style w:type="paragraph"{" w:customStyle=\"1\"" if custom else ""} '
            f'w:styleId="{sid}"><w:name w:val="{name}"/><w:basedOn w:val="{based}"/>'
            f'{extra}<w:qFormat/>'
            f'<w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>')


def heading(n, size, before, after, page_break):
    pb = "<w:pageBreakBefore/>" if page_break else ""
    return pstyle(
        f"Heading{n}", f"heading {n}", "Normal",
        ppr=f'<w:keepNext/><w:keepLines/>{pb}<w:spacing w:before="{before}" '
            f'w:after="{after}" w:line="240" w:lineRule="auto"/><w:jc w:val="left"/>'
            f'<w:outlineLvl w:val="{n-1}"/>',
        rpr=f'{FONT}<w:b/><w:bCs/><w:color w:val="{HEAD}"/>'
            f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>',
        extra='<w:next w:val="BodyText"/><w:uiPriority w:val="9"/>')


def styles(xml):
    xml = re.sub(r"<w:rFonts [^>]*/>", FONT, xml)
    xml = re.sub(r"<w:rFonts\s[^>]*?/>", FONT, xml, flags=re.S)
    xml = re.sub(
        r"<w:rPrDefault>.*?</w:rPrDefault>",
        lambda m: re.sub(r'(<w:sz(?:Cs)? w:val=")\d+', r"\g<1>22", m.group(0)),
        xml, flags=re.S)
    xml = re.sub(r'w:lang w:val="en-US"', 'w:lang w:val="es-AR"', xml)
    body = ('<w:keepLines w:val="0"/><w:spacing w:before="0" w:after="120" '
            'w:line="276" w:lineRule="auto"/><w:jc w:val="both"/>')
    xml = set_style(xml, "BodyText", pstyle("BodyText", "Body Text", "Normal", ppr=body,
                    extra='<w:link w:val="BodyTextChar"/>'))
    xml = set_style(xml, "FirstParagraph", pstyle("FirstParagraph", "First Paragraph",
                    "BodyText", custom=True, extra='<w:next w:val="BodyText"/>'))
    # Compact (tight lists): same face, smaller gaps, left aligned.
    xml = set_style(xml, "Compact", pstyle("Compact", "Compact", "BodyText", custom=True,
                    ppr='<w:spacing w:before="20" w:after="20"/><w:jc w:val="left"/>'))
    xml = set_style(xml, "TableText", pstyle("TableText", "Table Text", "Normal", custom=True,
                    ppr='<w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/>'
                        '<w:jc w:val="left"/>',
                    rpr='<w:sz w:val="20"/><w:szCs w:val="20"/>'))
    for sid, nm, sz in (("TableTextSmall", "Table Text Small", 16),
                        ("TableTextXSmall", "Table Text XSmall", 15)):
        xml = set_style(xml, sid, pstyle(sid, nm, "TableText", custom=True,
                        rpr=f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'))
    xml = set_style(xml, "Heading1", heading(1, 32, 0, 240, True))
    xml = set_style(xml, "Heading2", heading(2, 26, 280, 120, False))
    xml = set_style(xml, "Heading3", heading(3, 23, 200, 80, False))
    xml = set_style(xml, "TOCHeading", pstyle(
        "TOCHeading", "TOC Heading", "Heading1",
        ppr='<w:pageBreakBefore w:val="0"/><w:outlineLvl w:val="9"/>',
        extra='<w:next w:val="BodyText"/><w:uiPriority w:val="39"/>'))
    for lvl, ind, bold in ((1, 0, "<w:b/>"), (2, 220, "")):
        xml = set_style(xml, f"TOC{lvl}", pstyle(
            f"TOC{lvl}", f"toc {lvl}", "Normal",
            ppr=f'<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{TEXT_W}"/></w:tabs>'
                f'<w:spacing w:before="{80 if lvl == 1 else 0}" w:after="40"/>'
                f'<w:ind w:left="{ind}"/><w:jc w:val="left"/>',
            rpr=bold, extra='<w:next w:val="Normal"/><w:uiPriority w:val="39"/>'))
    cap = ('<w:keepLines/><w:spacing w:before="120" w:after="120" w:line="240" '
           'w:lineRule="auto"/><w:jc w:val="left"/>')
    xml = set_style(xml, "Caption", pstyle("Caption", "Caption", "Normal", ppr=cap,
                    rpr=f'<w:b/><w:bCs/><w:color w:val="{INK}"/><w:sz w:val="20"/>'
                        '<w:szCs w:val="20"/>'))
    xml = set_style(xml, "TableCaption", pstyle("TableCaption", "Table Caption", "Caption",
                    custom=True, ppr="<w:keepNext/>"))
    xml = set_style(xml, "ImageCaption", pstyle("ImageCaption", "Image Caption", "Caption",
                    custom=True, ppr='<w:jc w:val="center"/>'))
    xml = set_style(xml, "Figure", pstyle("Figure", "Figure", "Normal", custom=True,
                    ppr='<w:spacing w:before="120" w:after="60"/><w:jc w:val="center"/>'))
    xml = set_style(xml, "CaptionedFigure", pstyle("CaptionedFigure", "Captioned Figure",
                    "Figure", custom=True, ppr="<w:keepNext/>"))
    # Keep the literal code selectable; distinguish listings with a light band.
    xml = set_style(xml, "SourceCode", pstyle(
        "SourceCode", "Source Code", "Normal", custom=True,
        ppr='<w:shd w:val="clear" w:color="auto" w:fill="F0F3F6"/>'
            '<w:spacing w:before="120" w:after="120" w:line="240" w:lineRule="auto"/>'
            '<w:ind w:left="120" w:right="120"/><w:jc w:val="left"/>',
        rpr='<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/>'
            '<w:sz w:val="17"/><w:szCs w:val="17"/>'))
    # These named styles are used only by the cover, not the report headings.
    navy = "223D67"
    band = f'<w:shd w:val="clear" w:color="auto" w:fill="{navy}"/>'
    rule = f'<w:pBdr><w:bottom w:val="single" w:sz="8" w:space="8" w:color="{navy}"/></w:pBdr>'
    cover = {
        "CoverMark": (22, "FFFFFF", 240, 120, band, ""),
        "CoverInstitution": (22, "FFFFFF", 120, 140, band, "<w:b/>"),
        "CoverHeading": (50, navy, 760, 60, "", "<w:b/>"),
        "CoverSemester": (23, navy, 60, 160, "", ""),
        "CoverTopic": (34, navy, 420, 540, rule, "<w:b/><w:i/>"),
        "CoverBand": (22, "FFFFFF", 120, 120, band, ""),
    }
    for sid, (size, color, before, after, decoration, emphasis) in cover.items():
        xml = set_style(xml, sid, pstyle(
            sid, sid, "Normal", custom=True,
            ppr=f'<w:keepLines/>{decoration}<w:spacing w:before="{before}" w:after="{after}"/>'
                '<w:jc w:val="center"/>',
            rpr=f'{FONT}{emphasis}<w:color w:val="{color}"/>'
                f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'))
    # Cover: Title / Subtitle (pandoc custom-style divs), centered, no justification.
    xml = set_style(xml, "Title", pstyle(
        "Title", "Title", "Normal", extra='<w:next w:val="BodyText"/>',
        ppr='<w:spacing w:before="240" w:after="240" w:line="240" w:lineRule="auto"/>'
            '<w:jc w:val="center"/>',
        rpr=f'{FONT}<w:b/><w:color w:val="{INK}"/><w:sz w:val="36"/><w:szCs w:val="36"/>'))
    xml = set_style(xml, "Subtitle", pstyle(
        "Subtitle", "Subtitle", "Title", extra='<w:next w:val="BodyText"/>',
        ppr='<w:spacing w:before="60" w:after="60"/>',
        rpr='<w:b w:val="0"/><w:sz w:val="26"/><w:szCs w:val="26"/>'))
    tbl = (
        '<w:style w:type="table" w:default="1" w:styleId="Table"><w:name w:val="Table"/>'
        '<w:basedOn w:val="TableNormal"/><w:qFormat/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/>'
        f'<w:tblBorders><w:top {BORDER}/><w:left {BORDER}/><w:bottom {BORDER}/>'
        f'<w:right {BORDER}/><w:insideH {BORDER}/><w:insideV {BORDER}/></w:tblBorders>'
        '<w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="60" w:type="dxa"/>'
        '<w:bottom w:w="40" w:type="dxa"/><w:right w:w="60" w:type="dxa"/></w:tblCellMar>'
        '</w:tblPr><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
        '<w:tblStylePr w:type="firstRow"><w:rPr><w:b/><w:bCs/><w:color w:val="1F1F1F"/></w:rPr><w:tcPr>'
        '<w:shd w:val="clear" w:color="auto" w:fill="C6D4EE"/><w:vAlign w:val="center"/>'
        '</w:tcPr></w:tblStylePr></w:style>')
    return set_style(xml, "Table", tbl)


FOOTER = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<w:ftr xmlns:w="{W_NS}"><w:p><w:pPr><w:pStyle w:val="Footer"/><w:jc w:val="center"/>'
    '</w:pPr><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>2</w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')
EMPTY_FOOTER = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<w:ftr xmlns:w="{W_NS}"><w:p><w:pPr><w:pStyle w:val="Footer"/></w:pPr></w:p></w:ftr>')
SECT = (
    '<w:sectPr><w:footerReference w:type="default" r:id="rIdFooterDefault"/>'
    '<w:footerReference w:type="first" r:id="rIdFooterFirst"/>'
    '<w:footnotePr><w:numRestart w:val="eachSect"/></w:footnotePr>'
    f'<w:pgSz w:w="{PAGE_W}" w:h="{PAGE_H}"/>'
    f'<w:pgMar w:top="{MARGIN}" w:right="{MARGIN}" w:bottom="{MARGIN}" w:left="{MARGIN}" '
    f'w:header="709" w:footer="709" w:gutter="0"/><w:titlePg/></w:sectPr>')
REL = ('<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
       'relationships/footer" Target="%s"/>')
CT = ('<Override PartName="/word/%s" ContentType="application/vnd.openxmlformats-'
      'officedocument.wordprocessingml.footer+xml"/>')


def reference(path):
    def fn(name, data):
        text = data.decode("utf-8") if name.endswith((".xml", ".rels")) else None
        if name == "word/styles.xml":
            return styles(text).encode()
        if name == "word/document.xml":
            text = re.sub(r"<w:sectPr>.*?</w:sectPr>", lambda m: SECT, text, flags=re.S)
            return text.encode()
        if name == "word/_rels/document.xml.rels":
            add = REL % ("rIdFooterDefault", "footer1.xml") + REL % ("rIdFooterFirst", "footer2.xml")
            return text.replace("</Relationships>", add + "</Relationships>").encode()
        if name == "[Content_Types].xml":
            return text.replace("</Types>", CT % "footer1.xml" + CT % "footer2.xml" + "</Types>").encode()
        return data
    fn.extra = {"word/footer1.xml": FOOTER, "word/footer2.xml": EMPTY_FOOTER}
    rewrite(path, fn)
    # Footer style may be missing in pandoc's reference: ensure it exists.
    def ensure(name, data):
        if name == "word/styles.xml" and b'w:styleId="Footer"' not in data:
            x = data.decode()
            x = set_style(x, "Footer", pstyle("Footer", "footer", "Normal", ppr="<w:jc w:val=\"center\"/>",
                          rpr='<w:sz w:val="20"/>'))
            return x.encode()
        return data
    ensure.extra = {}
    rewrite(path, ensure)


# ---------------------------------------------------------------- post mode
def cell_text(tc):
    return re.sub(r"<[^>]+>", "", " ".join(re.findall(r"<w:t(?: [^>]*)?>[^<]*</w:t>", tc)))


def fix_table(tbl, index):
    rows = re.findall(r"<w:tr[ >].*?</w:tr>", tbl, re.S)
    grid = re.search(r"<w:tblGrid>.*?</w:tblGrid>", tbl, re.S)
    ncols = len(re.findall(r"<w:gridCol ", grid.group(0)))
    longest, total = [4] * ncols, [0] * ncols
    for r in rows:
        for c, tc in enumerate(re.findall(r"<w:tc>.*?</w:tc>", r, re.S)[:ncols]):
            t = cell_text(tc)
            longest[c] = max(longest[c], max((len(w) for w in re.split(r"[\s/\-]", t)), default=0))
            total[c] = max(total[c], len(t))
    pt, style = (10, "TableText") if ncols < 8 else (8, "TableTextSmall") if ncols < 10 \
        else (7.5, "TableTextXSmall")
    if index == 0 and ncols == 2:
        widths = [2400, 4600]  # cover table: 7000 twips, centered
    else:
        # Floor: longest word (bold, ~105 twips/char at 10 pt) + cell margins.
        k = 11.6 * pt  # bold Calibri ~0.53 em per char, in twips
        floor = [int(l * k) + 140 for l in longest]
        want = [max(f, min(t, 60) * 90 + 200) for f, t in zip(floor, total)]
        if sum(floor) >= TEXT_W:
            widths = [int(f * TEXT_W / sum(floor)) for f in floor]
        else:
            spare = TEXT_W - sum(floor)
            need = [w - f for w, f in zip(want, floor)]
            ns = sum(need) or 1
            widths = [f + int(spare * n / ns) for f, n in zip(floor, need)]
        widths[-1] += TEXT_W - sum(widths)
    new_grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>"
    tbl = tbl.replace(grid.group(0), new_grid)
    tbl = re.sub(r"<w:tblW [^>]*/>", f'<w:tblW w:type="dxa" w:w="{sum(widths)}"/>', tbl, count=1)
    if "<w:tblLayout" not in tbl:
        tbl = tbl.replace("<w:tblLook", '<w:tblLayout w:type="fixed"/><w:tblLook', 1)
    if index == 0 and ncols == 2:
        tbl = re.sub(r"(<w:tblW [^>]*/>)", r'\1<w:jc w:val="center"/>', tbl, count=1)
    # per-cell widths follow the grid
    def cells(row):
        i = iter(widths)
        return re.sub(r"<w:tcPr\s*/>|<w:tcPr>(.*?)</w:tcPr>",
                      lambda m: f'<w:tcPr><w:tcW w:w="{next(i, widths[-1])}" w:type="dxa"/>'
                                f'{m.group(1) or ""}</w:tcPr>', row, flags=re.S)
    tbl = re.sub(r"<w:tr[ >].*?</w:tr>", lambda m: cells(m.group(0)), tbl, flags=re.S)
    return tbl.replace('<w:pStyle w:val="Compact"', f'<w:pStyle w:val="{style}"')


def add_keep(par, next_=True, lines=False):
    """Add <w:keepNext/> / <w:keepLines/> to a <w:p> element's pPr (after pStyle)."""
    flags = ("<w:keepNext/>" if next_ and "<w:keepNext/>" not in par else "") + \
            ("<w:keepLines/>" if lines and "<w:keepLines/>" not in par else "")
    m = re.match(r"(<w:p>\s*<w:pPr>\s*<w:pStyle [^>]*/>)", par)
    if m:
        return par.replace(m.group(1), m.group(1) + flags, 1)
    if re.match(r"<w:p>\s*<w:pPr>", par):
        return re.sub(r"(<w:pPr>)", r"\1" + flags, par, count=1)
    return par.replace("<w:p>", "<w:p><w:pPr>" + flags + "</w:pPr>", 1)


def keep_together(text):
    """Pagination: table/listing captions stay with their block; "Fuente:" lines stay
    with the block above (last table row or code paragraph). pandoc emits these
    captions as bold BodyText paragraphs, so the TableCaption keepNext never applies;
    the flags are set directly on the paragraphs."""
    par_re = re.compile(r"<w:p>(?:(?!<w:p>).)*?</w:p>", re.S)
    first_t = re.compile(r"<w:t(?: [^>]*)?>([^<]*)</w:t>")

    def txt(par):
        m = first_t.search(par)
        return m.group(1) if m else ""

    def is_caption(par):
        return (re.match(r"(Tabla|Listado) [A-Z0-9]+\.[0-9]+\.", txt(par)) is not None
                and "<w:b" in par.split("<w:t")[0])

    def is_source(par):
        return txt(par).startswith("Fuente:")

    # Fuente: lines first (need the original neighbours), then captions.
    edits = []  # (start, end, replacement)
    pars = list(par_re.finditer(text))
    for i, m in enumerate(pars):
        if not is_source(m.group(0)):
            continue
        edits.append((m.start(), m.end(), add_keep(m.group(0), next_=False, lines=True)))
        if i == 0:
            continue
        prev = pars[i - 1]
        if "</w:tbl>" in text[prev.end():m.start()]:
            tbl_end = text.rfind("</w:tbl>", 0, m.start())
            # last two rows of the table (a one-row tail can still be stranded)
            row_start = text.rfind("<w:tr", 0, text.rfind("<w:tr", 0, tbl_end))
            if row_start < text.rfind("<w:tbl>", 0, tbl_end):
                row_start = text.rfind("<w:tr", 0, tbl_end)
            row = text[row_start:tbl_end]
            row = par_re.sub(lambda r: add_keep(r.group(0)), row)
            # unsplittable last row, so keepNext moves the whole row with the Fuente line
            if "<w:cantSplit" not in row:
                if "<w:trPr>" in row:
                    row = row.replace("<w:trPr>", "<w:trPr><w:cantSplit/>", 1)
                else:
                    row = re.sub(r"(<w:tr(?: [^>]*)?>)", r"\1<w:trPr><w:cantSplit/></w:trPr>", row, count=1)
            edits.append((row_start, tbl_end, row))
        elif not is_caption(prev.group(0)):
            edits.append((prev.start(), prev.end(), add_keep(prev.group(0))))
    for i, m in enumerate(pars):
        if is_caption(m.group(0)):
            edits.append((m.start(), m.end(), add_keep(m.group(0), lines=True)))
            # a captioned table: keep header row + first data row with the caption
            nxt = pars[i + 1].start() if i + 1 < len(pars) else len(text)
            t0 = text.find("<w:tbl>", m.end())
            if 0 <= t0 < nxt:
                t1 = text.find("</w:tbl>", t0)
                rows = list(re.finditer(r"<w:tr[ >].*?</w:tr>", text[t0:t1], re.S))[:2]
                for r in rows:
                    new_row = par_re.sub(lambda q: add_keep(q.group(0)), r.group(0))
                    edits.append((t0 + r.start(), t0 + r.end(), new_row))
    for a, b, new in sorted(set(edits), reverse=True):
        text = text[:a] + new + text[b:]
    return text


def post(path):
    def fn(name, data):
        if name == "word/settings.xml":
            # Word 2013+ layout mode (without it Word opens in compatibility mode and
            # does not honor keep-with-next across table rows).
            st = data.decode("utf-8")
            if "compatibilityMode" not in st:
                compat = ('<w:compat><w:compatSetting w:name="compatibilityMode" '
                          'w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>')
                # schema order: w:compat comes before w:rsids / w:themeFontLang
                anchor = "<w:rsids>" if "<w:rsids>" in st else "<w:themeFontLang"
                st = st.replace(anchor, compat + anchor, 1)
            return st.encode("utf-8")
        if name != "word/document.xml":
            return data
        text = data.decode("utf-8")
        n = iter(range(10**6))
        text = re.sub(r"<w:tbl>.*?</w:tbl>", lambda m: fix_table(m.group(0), next(n)),
                      text, flags=re.S)
        # Air between a table and the paragraph right after it (the "Fuente:" line).
        # The cover's Subtitle paragraphs keep their own (centered) alignment.
        text = re.sub(r'(</w:tbl>\s*<w:p>\s*<w:pPr>)(\s*<w:pStyle w:val="(?!(?:Subtitle|CoverBand)")[A-Za-z]+"\s*/>)',
                      r'\1\2<w:spacing w:before="120"/><w:jc w:val="left"/>', text)
        text = keep_together(text)
        return text.encode()
    fn.extra = {}
    rewrite(path, fn)


if __name__ == "__main__":
    mode, target = sys.argv[1:3]
    {"reference": reference, "post": post}[mode](target)
