from collections import namedtuple, OrderedDict
from itertools import chain
from hashlib import sha1
import copy
import io
import numpy as np

from anytree import Node, RenderTree

from reportlab.platypus import Table, TableStyle, Image, Paragraph, Spacer, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate, NextPageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus.frames import Frame
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import matplotlib.pyplot as plt
import matplotlib
import pandas as pd


pdfmetrics.registerFont(TTFont('Calibri-Bold', r"C:/Windows/Fonts/calibrib.ttf"))
pdfmetrics.registerFont(TTFont('Calibri', r"C:/Windows/Fonts/calibri.ttf"))
pdfmetrics.registerFont(TTFont('Calibri-Italic', r"C:/Windows/Fonts/calibrii.ttf"))
pdfmetrics.registerFont(TTFont('Calibri-Bold-Italic', r"C:/Windows/Fonts/calibriz.ttf"))
# pdfmetrics.registerFont(TTFont('Calibri-Light', r"C:/Windows/Fonts/calibril.ttf"))
# pdfmetrics.registerFont(TTFont('Calibri-Light-Italic', r"C:/Windows/Fonts/calibrili.ttf"))
pdfmetrics.registerFontFamily(
    'Calibri',
    normal='Calibri',
    bold='Calibri-Bold',
    italic='Calibri-Italic',
    boldItalic='Calibri-Bold-Italic',
)



class MyDocTemplate(BaseDocTemplate):
    """BaseDocTemplate subclass set up for clickable Table of Contents"""

    def __init__(self, filename, **kw):
        self.allowSplitting = 0
        BaseDocTemplate.__init__(self, filename, **kw)
        self.pagesize = letter

    def afterFlowable(self, flowable):
        """Register TOC entries."""
        if flowable.__class__.__name__ == 'Paragraph':

            text = flowable.getPlainText()
            style = flowable.style.name
            if style == 'Heading1':
                level = 0
            elif style == 'Heading2':
                level = 1
            elif style == 'Heading3':
                level = 2
            #             elif style == 'Heading4':
            #                 level = 3
            else:
                return
            E = [level, text, self.page]
            # if we have a bookmark name, append that to our notify data
            bn = getattr(flowable, '_bookmarkName', None)
            if bn is not None: E.append(bn)
            self.notify('TOCEntry', tuple(E))


def make_doc(filename, title='Generic Title', title_page=None, content_page=None, font='Helvetica'):
    """Return MyDocTemplate instance with PageTemplates"""
    doc = MyDocTemplate(filename, pageSize=letter)

    if not title_page:
        def title_page(canvas, doc):
            """Create generic title page."""
            canvas.saveState()
            canvas.setFont(FONT, 36)
            canvas.drawCentredString(306, 600, title)
            canvas.restoreState()

    if not content_page:
        def content_page(canvas, doc):
            canvas.saveState()
            canvas.setFont(font, 12)
            #         canvas.drawRightString(7.5 * inch, .8 * inch, "Page %d | %s   %s" % (doc.page, model, footer_test_date))
            canvas.restoreState()

    frameT = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id='normal',
        #         showBoundary=1,
    )
    doc.addPageTemplates([
        PageTemplate(id='TitlePage', frames=frameT, onPage=title_page),
        PageTemplate(id='ContentPage', frames=frameT, onPage=content_page)
    ])
    return doc


def do_heading(text, sty, numbering=True):
    """Return heading with modifications necessary for TOC functionality."""
    if numbering:
        heading = {
            'Heading1': "<seq id='h1'/>.<seqreset id='h2'/><seqreset id='h3'/><seqreset id='h4'/> {}",
            'Heading2': "<seq id='h1' inc='no'/>.<seq id='h2'/><seqreset id='h3'/><seqreset id='h4'/> {}",
            'Heading3': "<seq id='h1' inc='no'/>.<seq id='h2' inc='no'/>.<seq id='h3'/><seqreset id='h4'/> {}",
            #             'Heading4' : "<seq id='h1' inc='no'/>.<seq id='h2' inc='no'/>.<seq id='h3' inc='no'/>.<seq id='h4'/> {}",
            'Heading4': '{}'
        }
        text = heading.get(sty.name, '{}').format(text)
    # create bookmarkname
    s = text + sty.name
    bn = sha1(s.encode(encoding='UTF-8')).hexdigest()
    # modify paragraph text to include an anchor point with name bn
    h = Paragraph(text + '<a name="%s"/>' % bn, sty)
    # store the bookmark name on the flowable so afterFlowable can see this
    h._bookmarkName = bn
    return h


# Paragraph styles

FONT = 'Calibri'
HEADER_FONT = 'Calibri-Bold'
PARAGRAPH_STYLES = {
    'centered': ParagraphStyle(name='centered',
                               fontName=HEADER_FONT,
                               fontSize=20,
                               leading=16,
                               alignment=1,
                               spaceAfter=20),

    'Heading1': ParagraphStyle(name='Heading1',
                               fontName=HEADER_FONT,
                               fontSize=14,
                               leading=16),

    'Heading2': ParagraphStyle(name='Heading2',
                               fontName=HEADER_FONT,
                               fontSize=12,
                               leading=14,
                               spaceAfter=10),

    'Heading3': ParagraphStyle(name='Heading3',
                               fontName=HEADER_FONT,
                               fontSize=12,
                               leading=14,
                               spaceAfter=10),

    'Heading4': ParagraphStyle(name='Heading4',
                               fontName=HEADER_FONT,
                               fontSize=12,
                               leading=14,
                               spaceAfter=10),

    'Heading': ParagraphStyle(name='Heading',
                              fontName=HEADER_FONT,
                              fontSize=12,
                              leading=14,
                              spaceAfter=10)
}

normal = getSampleStyleSheet()['Normal']
normal.fontName = FONT
PARAGRAPH_STYLES['Normal'] = normal

centered = copy.copy(normal)
centered.alignment = 1
PARAGRAPH_STYLES['Centered'] = centered

table = copy.copy(normal)
table.leading = 0
PARAGRAPH_STYLES['TableNormal'] = table

table_centered = copy.copy(centered)
table_centered.leading = 12
PARAGRAPH_STYLES['TableCentered'] = table_centered

PARAGRAPH_STYLES['TOCHeadings'] = [
    ParagraphStyle(fontName=FONT, fontSize=14, name='TOCHeading1',
                   leftIndent=20, firstLineIndent=-20, spaceBefore=5, leading=16),
    ParagraphStyle(fontName=FONT, fontSize=12, name='TOCHeading2',
                   leftIndent=40, firstLineIndent=-20, spaceBefore=0, leading=12),
    ParagraphStyle(fontName=FONT, fontSize=10, name='TOCHeading3',
                   leftIndent=60, firstLineIndent=-20, spaceBefore=0, leading=12),
    ParagraphStyle(fontName=FONT, fontSize=10, name='TOCHeading4',
                   leftIndent=100, firstLineIndent=-20, spaceBefore=0, leading=12),
]

# In[6]:


GRID_STYLES = {
    'normal': TableStyle([('BACKGROUND', (0, 0), (-1, 0), 'lightgrey'),
                          ('FONTNAME', (0, 0), (-1, -1), FONT),
                          ('GRID', (0, 0), (-1, -1), 0.25, 'black'),
                          ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                          ('ALIGN', (1, 0), (-1, -1), 'CENTER')
                          ]),
    'persistence_criteria': TableStyle([('BACKGROUND', (0, 0), (-1, 0), 'lightgrey'),
                                        ('FONTNAME', (0, 0), (-1, -1), FONT),
                                        ('GRID', (0, 0), (-1, -1), 0.25, 'black'),
                                        ('SPAN', (0, 1), (0, 2)),
                                        ('SPAN', (0, 3), (0, 4)),
                                        ('SPAN', (0, 5), (0, 6)),
                                        ('VALIGN', (0, 0), (-1, -1), 'CENTRE')
                                        ]),
    'test_specs': TableStyle([('BACKGROUND', (0, 0), (0, -1), 'lightgrey'),
                              ('FONTNAME', (0, 0), (-1, -1), FONT),
                              ('GRID', (0, 0), (-1, -1), 0.25, 'black'),
                              ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
                              ]),
    'frame': TableStyle([('ALIGN', (0, 0), (0, 0), 'CENTER'),
                         ('GRID', (0, 0), (-1, -1), 0.25, 'black'),
                         ('VALIGN', (0, 0), (0, 0), 'MIDDLE')
                         ]),
}


# In[7]:


# flowable converters
def make_paragraph(text, style=PARAGRAPH_STYLES['Normal']):
    """Return Paragraph object from string."""
    return Paragraph(text, style)


def make_table(table_df, grid_style=GRID_STYLES['normal'], header=True, **kw):
    """Return a Table object from pandas DataFrame"""
    if header:
        table_data = np.vstack((list(table_df), np.array(table_df))).tolist()
    else:
        table_data = np.array(table_df).tolist()
    test_col = None
    # for i, col in enumerate(table_data[0]):
    #     if 'Test' in col:
    #         test_col = i
    if 'Test' in table_data[0]:
        test_col = table_data[0].index('Test')
    elif 'Test Number' in table_data[0]:
        test_col = table_data[0].index('Test Number')
    cleaned = []
    for i, row in enumerate(table_data):
        clean_row = []
        for j, cell_text in enumerate(row):
            if test_col != None and i > 0 and j == test_col and str(cell_text)[0].isnumeric() and cell_text % 1 == 0:
                cell_text = int(cell_text)
            if pd.isnull(cell_text):
                cell_text = ''

            clean_row.append(Paragraph(str(cell_text), PARAGRAPH_STYLES['TableCentered']))
        cleaned.append(clean_row)
    table_data = cleaned
    table = Table(table_data, style=grid_style, repeatRows=1, **kw)
    return table


def make_img(plot, max_width=439, max_height=650, **kw):
    """Return an Image object from a matplotlib.pyplot figure."""
    imgdata = io.BytesIO()
    plot.savefig(imgdata)
    imgdata.seek(0)
    img = Image(imgdata)
    # resize image
    aspect_ratio = img.imageWidth / img.imageHeight
    if max_height * aspect_ratio > max_width:
        # if width is limiting dimension
        img.drawWidth, img.drawHeight = max_width, max_width / aspect_ratio
    else:
        # if height is limiting dimension
        img.drawWidth, img.drawHeight = max_height * aspect_ratio, max_height
    return img


def flowable_factory(content, **kw):
    """Return appropriate flowable object from given content type"""
    factory = {
        type(plt.gcf()): make_img,
        str: make_paragraph,
        pd.core.frame.DataFrame: make_table
    }
    return factory[type(content)](content, **kw)


class Element(namedtuple('Element', ['content', 'spacer'])):
    """A namedtuple with two fields, one for a content flowable and one for a spacer flowable"""

    @classmethod
    def from_content(cls, content, header=False, level=1, numbering=True, spacer_height=.15 * inch, **kw):
        """Return an Element object containing appropriate flowables from raw content."""
        if header:
            style = PARAGRAPH_STYLES[f'Heading{level}']
            content_flowable = do_heading(content, style, numbering=numbering)
        else:
            content_flowable = flowable_factory(content, **kw)

        spacer = Spacer(height=spacer_height, width=0)
        return cls(content_flowable, spacer)

    # @classmethod
    # def from_title(cls, title, level, spacer_height=.15*inch):
    #     """Return an Element containing a report Heading from a string."""
    #     style = PARAGRAPH_STYLES[f'Heading{level}']
    #     heading = do_heading(title, style)
    #     spacer = Spacer(height=spacer_height, width=0)
    #     return cls(heading, spacer)


class Section(Node):
    """This is a container class for Element objects representing sections and subsections of a report."""

    def __init__(self, name, elements=OrderedDict(), page_break=True, **kwargs):
        super().__init__(name, **kwargs)
        self.elements = elements
        self.story_start = []
        self.page_break = page_break

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        if self.page_break:
            key = list(self.elements.keys())[-1]
            old_elem = list(self.elements.values())[-1]
            new_elem = Element(old_elem.content, PageBreak())
            self.elements[key] = new_elem

    @property
    def sections(self):
        """Access dictionary of child Section objects"""
        return {child.name: child for child in self.children}

    def new_section(self, title, numbering=True, **kw):
        """Create and Return new child Section (subsection)."""
        new_section = Section(name=title, elements={}, parent=self, **kw)
        new_section.elements['title'] = Element.from_content(title, header=True, numbering=numbering,
                                                             level=self.depth + 1)
        return new_section

    def create_element(self, name, content, **kw):
        """Create a new Element from raw content"""
        self.elements[name] = Element.from_content(content, **kw)

    def story(self):
        """Return report as a list ready to be passed to MyDocTemplate multiBuild method."""
        tree = RenderTree(self)
        story = [
            Paragraph("<seqreset id='h1'/>", PARAGRAPH_STYLES['Normal']),
            NextPageTemplate('ContentPage'),
            PageBreak(),
            Paragraph('<b>Table of Contents</b>', PARAGRAPH_STYLES['centered']),
            TableOfContents(levelStyles=PARAGRAPH_STYLES['TOCHeadings']),
            PageBreak()
        ]

        for row in list(tree)[1:]:
            elements = list(row.node.elements.values())
            flowables = list(chain(*elements))
            story += flowables
        return story