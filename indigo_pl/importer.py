# -*- coding: utf-8 -*-
import re

from bs4 import BeautifulSoup
from indigo_api.importers.base import Importer
from indigo.plugins import plugins
from platform import node


@plugins.register('importer')
class ImporterPL(Importer):
    """ Importer for the Polish tradition.

    Expects the input PDF files to be in the format produced by the Online Legal Database
    (= "Internetowy System Aktów Prawnych" or "ISAP") of the Polish parliament (= "Sejm")
    for unified texts (= "tekst ujednolicony"). 

    Unified texts are NOT the official consolidated texts (= "tekst jednolity"), but ISAP
    produces them much more often, and they are of very good quality, practically the same as 
    consolidated texts.

    See http://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU20120001512 for an example law 
    with unified text - the PDF next to "Tekst ujednolicony:".
    """
    
    NO_FONTSIZE = -1
    """Magic number to indicate that we couldn't find fontsize for the node that has it."""
    
    PAGE_NUM_MULTIPLIER = 100000
    """We increase the "top" attribute of each <text> tag in the PDF by this number * page number
    of page the tag is on. This way the attribute is monotonically increasing (at least for the
    main law text itself - not necessarily for header, footer, footnotes).
    """

    SUPERSCRIPT_START = "@@SUPERSCRIPT@@"
    """Special label placed in law plaintext before a superscript string."""

    SUPERSCRIPT_END = "##SUPERSCRIPT##"
    """Special label placed in law plaintext after a superscript string."""

    HEADER_END_OFFSET = 50
    """How far from top of page we assume header is over."""

    FOOTER_START_OFFSET = 1060
    """How far from top of page we assume footer starts."""

    RIGHT_MARGIN_START_OFFSET = 630
    """How far from left edge of page we assume right margin starts."""

    SIGNATURE_REGEX = '^\s*(Dz\.U\.|M\.P\.)\s+\d{4}\s+(Nr\s+\d+\s+)?poz\.\s+\d+\s*$'
    """Regex catching line containing only the law signature, e.g. "Dz.U. 2018 poz. 1234"."""

    LEVEL0_PREFIX_REGEX = ur"(?:Art.|§)\s+\d+[a-z]*(?:@@SUPERSCRIPT@@[^#]+##SUPERSCRIPT##)?\."
    """Regex catching line starts for level 0 law hierarchy units."""

    LEVEL1_PREFIX_REGEX = ur"(?:§\s+)?\d+[a-z]*(?:@@SUPERSCRIPT@@[^#]+##SUPERSCRIPT##)?\."
    """Regex catching line starts for level 1 law hierarchy units."""

    INDENT_REGEX = ur"^@@INDENT\d@@"
    """Regex catching lines starting with indent mark."""

    LEVEL0_PREFIX_WITH_INDENT = INDENT_REGEX + LEVEL0_PREFIX_REGEX
    """Regex catching line starts for level 0 law hierarchy units, with indent info prepended."""

    POINT_PREFIX_WITH_INDENT = INDENT_REGEX + ur"\d+[a-z]*(@@SUPERSCRIPT@@[^#]+##SUPERSCRIPT##)?\) "
    """Regex catching line starts for "point" law hierarchy units, with indent info prepended."""

    LETTER_PREFIX_WITH_INDENT = INDENT_REGEX + ur"[a-z]+(@@SUPERSCRIPT@@[^#]+##SUPERSCRIPT##)?\) "
    """Regex catching line starts for "letter" law hierarchy units, with indent info prepended."""

    DASH_PREFIX_WITH_INDENT = INDENT_REGEX + ur"– "
    """Regex catching line starts with dashes, with indent info prepended."""
    
    DOUBLE_TIRET_PREFIX_WITH_INDENT = u"^@@INDENT3@@–\s+–\s+"
    """Regex catching line starts for double tirets, with indent info prepended."""

    TRIPLE_TIRET_PREFIX_WITH_INDENT = u"^@@INDENT4@@–\s+–\s+–\s+"
    """Regex catching line starts for triple tirets, with indent info prepended."""
    
    INDENT_LEVELS1 = [96, 130, 162, 189, 216, 248]
    """Most common indent levels in unified Polish law PDFs.
    
    Getting these numbers from statute: "o usługach zaufania oraz identyfikacji elektronicznej". 
    http://isap.sejm.gov.pl/isap.nsf/download.xsp/WDU20160001579/U/D20161579Lj.pdf
    """
    INDENT_LEVELS2 = [76, 111, 143, 170]
    """The other option for indent levels in unified Polish law PDFs.
    
    Getting these numbers from statute: "o odnawialnych źródłach energii".
    http://isap.sejm.gov.pl/isap.nsf/download.xsp/WDU20150000478/U/D20150478Lj.pdf
    """

    locale = ('pl', None, None)

    slaw_grammar = 'pl'

    def pdf_to_text(self, f):
        """Override of pdf_to_text from superclass, using "pdftohtml" instead of "pdftotext".
        We need the HTML (XML actually) with positional info to do some special preprocessing,
        such as recognizing superscripts or how much dashes are indented.

        Args:
            f: The input PDF file.
        """
        cmd = ["pdftohtml", "-zoom", "1.35", "-xml", "-stdout", f.name]
        code, stdout, stderr = self.shell(cmd)
        if code > 0:
            raise ValueError(stderr)
        return stdout.decode('utf-8')

    def reformat_text(self, text):
        """Override of reformat_text from superclass. Here we do our special preprocessing on
        XML, then strip XML tags, and return a plain text string which should finally be parsed
        into Akoma Ntoso.

        Args:
            text: String containing XML produced by pdf_to_text.

        Returns:
            str: Plain text containing the law.
        """
        xml = BeautifulSoup(text)
        self.assert_all_text_nodes_have_top_left_height_font_attrs(xml)
        self.remove_empty_text_nodes(xml)
        self.remove_header_and_footer(xml)
        self.remove_right_margin(xml)
        self.add_fontsize_to_all_text_nodes(xml)
        self.make_top_attribute_monotonically_increasing(xml)
        self.add_line_nums_to_law_text(xml)
        # At this point, all <text> nodes with most common "fontsize" have "line" attribute.
        self.undecorate_outgoing_and_upcoming_sections(xml)
        self.process_superscripts(xml)
        self.remove_footnotes(xml)
        self.assert_only_text_nodes_with_most_common_fontsize_left(xml)
        self.join_text_nodes_on_same_lines(xml)
        self.assert_each_text_node_has_increasing_line_attr(xml)
        self.add_indent_info_for_dashed_lines(xml)
        self.add_newline_if_level0_unit_starts_with_level1_unit(xml)
        text = self.xml_to_text(xml)
        text = self.join_hyphenated_words(text)
        text = self.remove_linebreaks(text)
        text = self.trim_lines(text)
        return text
    
    def assert_all_text_nodes_have_top_left_height_font_attrs(self, xml):
        """Make sure all the text XML nodes have all the required attributes, so that we don't
        have to check them later on.
        
        Args:
            xml: The XML to operate on, as a list of tags.
        """
        for page in xml.find_all("page"):
            for node in page.find_all("text"):
                if ((not node.has_attr("top")) or (not node.has_attr("height")) 
                    or (not node.has_attr("font")) or (not node.has_attr("left"))):
                    raise Exception("The following node on page [" + page["number"] 
                                    + "] doesn't have all the expected attributes: \n" + str(node))

    def remove_empty_text_nodes(self, xml):
        """Remove the XML nodes containing nothing or whitespace.
        
        Args:
            xml: The XML to operate on, as a list of tags.
        """
        for node in xml.find_all("text"):
            if re.match("^\s*$", node.get_text()):
                node.extract()

    def remove_header_and_footer(self, xml):
        """Modify the passed in XML by removing tags laying outside the area we know to be
        the actual law text, vertically. Generally, this will be the ISAP header, and footer
        containing page numbers.

        Args:
            xml: The XML to operate on, as a list of tags.
        """
        for tag in xml.find_all(self.is_header_or_footer):
            tag.extract()

    def is_header_or_footer(self, tag):
        """Check if the given tag lies on the page at a position known to be in header or footer.

        Args:
            tag: The tag to check.

        Returns:
            bool: True if tag is in header/footer, False otherwise.
        """
        divider = (self.PAGE_NUM_MULTIPLIER / 10)
        return ((tag.name == "text")
            and (((int(tag["top"]) % divider) <= self.HEADER_END_OFFSET) 
                 or ((int(tag["top"]) % divider) > self.FOOTER_START_OFFSET)))

    def remove_right_margin(self, xml):
        """Modify the passed in XML by removing tags laying outside the area we know to be
        the actual law text, to the right. Generally, these are notes about which sections are
        outgoing and upcoming.

        Args:
            xml: The XML to operate on, as a list of tags.
        """
        for tag in xml.find_all(self.is_right_margin):
            tag.extract()

    def is_right_margin(self, tag):
        """Check if the given tag lies on the page at a position known to be in the right margin.

        Args:
            tag: The tag to check.

        Returns:
            bool: True if tag is in the right margin, False otherwise.
        """
        return (tag.name == "text") and (int(tag["left"]) > self.RIGHT_MARGIN_START_OFFSET)

    def add_fontsize_to_all_text_nodes(self, xml):
        """Add info about font size to XML nodes. It can be found in XML nodes called <fontspec>,
        like this: <fontspec color="#000000" family="Times" id="0" size="10"></fontspec>. We
        match <text font="12345"> nodes with <fontspec id="12345"> node and create a "fontsize"
        attribute on the former.
        
        Args:
            xml: The XML to operate on, as a list of tags.
        """
        fonts_to_fontsizes = {}
        for node in xml.find_all("fontspec"):
            fonts_to_fontsizes[node["id"]] = node["size"]
        for node in xml.find_all("text"):
            node["fontsize"] = fonts_to_fontsizes.get(node["font"], self.NO_FONTSIZE)

    def make_top_attribute_monotonically_increasing(self, xml):
        """Increase "top" attribute of <text> nodes by 
        {page number <text> is on} * PAGE_NUM_MULTIPLIER. Then it'll be monotonically increasing.

        Args:
            xml: The XML to operate on, as a list of tags.
        """
        for page in xml.find_all("page"):
            num = int(page["number"])
            for node in page.find_all("text"):
                node["top"] = int(node["top"]) + self.PAGE_NUM_MULTIPLIER * num

    def add_line_nums_to_law_text(self, xml):
        """For all <text> tags that represent parts of the law text, add a "line" attribute
        saying which line number a given tag sits, counting from 1. Tags on the same line have
        the same "top" attribute.
              
        We make these assumptions:
        - Law text lines (as opposed e.g. to footnotes, headers, etc) have font size which is
          the most commonly occurring in the PDF.
        - PDF has the <text> tags corresponding to law text parts in such an order that the
          attribute pair (top, left) monotonically increases with each tag. What I mean by 
          increasing here is that EITHER of these two must increase with each new tag, and "top"
          must never decrease ("left" may decrease as "top" increases - when moving to new line).
          We ignore the lines that don't conform, assuming they are not the main law text.
        - Increasing / comparisons of "top" has a tolerance of 2 points. I'm not sure if this
          is needed, but just in case.
          
        Args:
            xml: The XML to operate on, as a list of tags.
        """
        self.assert_main_text_is_sorted(xml)
        last_top = 0
        line_num = 0
        for node in xml.find_all(name = "text", 
                                 attrs = {"fontsize": self.find_most_common_fontsize(xml)}):
            if (int(node["top"]) - 2 > last_top):
                last_top = int(node["top"])
                line_num = line_num + 1
            node["line"] = line_num
                
    def assert_main_text_is_sorted(self, xml):
        """Assert that for <text> nodes having the most common "fontsize", their attribute pair 
        (top, left) monotonically increases with each tag. What I mean by increasing here is that
        EITHER of these two must increase with each new tag, and "top" must never decrease
        ("left" may decrease as "top" increases - when moving to new line).

        Args:
            xml: The XML to operate on, as a list of tags.
        """
        most_common_fontsize = self.find_most_common_fontsize(xml)        
        last_top = 0
        last_left = 0
        last_width = 0
        for node in xml.find_all(name = "text", attrs = {"fontsize": most_common_fontsize}):            
            top = int(node["top"])
            left = int(node["left"])
            if (top - 2 < last_top) and (top + 2 > last_top):
                if (left <= last_left + last_width):
                    raise Exception("Non-increasing 'left' attribute: [" + str(left) 
                        + "] at node (last_left = [" + str(last_left) + "]): \n" + str(node)) 
            elif (top > last_top):
                last_top = top
            else:
                raise Exception("Non-increasing 'top' attribute: [" + str(top) 
                    + "] at node (last_top = [" + str(last_top) + "]): \n" + str(node))
            last_left = left
            last_width = int(node["width"])

    def find_most_common_fontsize(self, xml):
        """Returns the fontsize value that most of <text> nodes in the doc have.

        Args:
            xml: The XML to operate on, as a list of tags.

        Returns:
            int: The font size value that most of <text> nodes have.
        """
        fontsizes = {}
        for node in xml.find_all("text"):
            fontsize = int(node["fontsize"])
            fontsizes[fontsize] = ((fontsizes[fontsize] + 1) if fontsizes.has_key(fontsize) else 1)
        most_common_fontsize = max(fontsizes, key = fontsizes.get)
        if (most_common_fontsize == self.NO_FONTSIZE):
            raise Exception("Most common fontsize in the PDF can't be the marker for no font size.")
        return most_common_fontsize

    def undecorate_outgoing_and_upcoming_sections(self, xml):
        """In ISAP unified texts, when a given article, etc is changing on some future date, they
        first print the current version in italics and inside '[ ... ]' markers, and immediately
        after, they print the upcoming version in bold and inside '< ... >' markers.

        This function removes the '[', ']', '<', '>' markers. We rely on the person doing manual
        post-processing to remove the section that's currently not effective and leave the section
        that's currently in force.

        Args:
            xml: The XML to operate on, as a list of tags.
        """

        is_in_outgoing_part = False
        is_in_upcoming_part = False
        for node in xml.find_all('text'):
            i = node.find_all('i') # Find italics.
            b = node.find_all('b') # Find bold.
            text = node.get_text().strip()
            btext = b[0].get_text().strip() if (len(b) == 1) else "!@#$%^&*()" # else garbage.
            itext = i[0].get_text().strip() if (len(i) == 1) else "!@#$%^&*()" # else garbage.

            if (is_in_outgoing_part and is_in_upcoming_part):
                raise Exception("Impossible to be in outgoing and upcoming section at same time.")
            elif (is_in_outgoing_part and not is_in_upcoming_part):
                if (itext != text):
                    raise Exception("Expected italics while being in outgoing section.")
                if text.endswith("]"):
                    is_in_outgoing_part = False
                    node.string = text.rstrip("]")
            elif (not is_in_outgoing_part and is_in_upcoming_part):
                if (btext != text):
                    raise Exception("Expected bold while being in upcoming section.")
                if text.endswith(">"):
                    is_in_upcoming_part = False
                    node.string = text.rstrip(">")
            else:
                if (itext == text) and text.startswith("["):
                    node.string = text.lstrip("[").rstrip("]")
                    if not text.endswith("]"): # Needed in case outgoing section is one line only.
                        is_in_outgoing_part = True
                elif (btext == text) and text.startswith("<"):
                    node.string = text.lstrip("<").rstrip(">")
                    if not text.endswith(">"): # Needed in case upcoming section is one line only.
                        is_in_upcoming_part = True
                # For cases like: "<text ...><b>Art. 22c.</b> <i>[1. Some text </i></text>."
                elif ((btext + u" " + itext == text)
                    and btext.startswith("Art.") and itext.startswith("[")):
                    node.string = btext + u" " + itext.lstrip("[").rstrip("]")
                    if not itext.endswith("]"): # Needed in case outgoing section is one line only.
                        is_in_outgoing_part = True

    def process_superscripts(self, xml):
        """Modify the passed in XML by searching for tags which represent superscript numbering and
        combining them with neighboring tags in such a way that superscripts are no longer
        indicated by XML positional info (lower font height and lower offset from page top than
        the rest of line), but by special surrounding text (^^SUPERSCRIPT^^ before and
        $$SUPERSCRIPT$$ after).

        Args:
            xml: The XML to operate on, as a list of tags.
        """
        text_nodes = xml.find_all('text')

        superscript_pattern = re.compile("^[a-z0-9]+$")
        # TODO: We may relax the node_plus_two_pattern a bit, particularly removing the requirement
        # of a period at the beginning. When a division number is mentioned from another place,
        # the period is not always there.
        node_plus_two_pattern = re.compile("^\. .*")
        n = len(text_nodes)
        if (n < 3):
            return

        nodes_to_remove = []

        for _ in xrange(0, n - 3):
            node = text_nodes.pop(0)
            node_plus_one = text_nodes[0]
            node_plus_two = text_nodes[1]

            node_txt = node.get_text().strip()
            node_plus_one_txt = node_plus_one.get_text().strip()
            node_plus_two_txt = node_plus_two.get_text().strip()

            if not superscript_pattern.match(node_plus_one_txt):
                continue

            if not node_plus_two_pattern.match(node_plus_two_txt):
                continue

            # node and node_plus_two must have the same height.
            if int(node["height"]) != int(node_plus_two["height"]):
                continue

            # node_plus_one must have lower height than node/node_plus_two (smaller font).
            if int(node["height"]) <= int(node_plus_one["height"]):
                continue

            # node and node_plus_two must be in same line.
            if int(node["top"]) != int(node_plus_two["top"]):
                continue

            # node_plus_one must not be below the line of node/node_plus_two.
            if int(node["top"]) < int(node_plus_one["top"]):
                continue

            # Concat all three nodes, surrounding text of node_plus_one with special labels.
            # Put concatenated text in node, remove node_plus_one & node_plus_two.
            node.string = (node_txt + self.SUPERSCRIPT_START + node_plus_one_txt
                + self.SUPERSCRIPT_END + node_plus_two_txt)
            nodes_to_remove.append(node_plus_one)
            nodes_to_remove.append(node_plus_two)

        for node in nodes_to_remove:
            node.extract()

    def remove_footnotes(self, xml):
        """Modify the passed in XML by searching for tags which have font size different than 
        the most common value. Remove all such tags. This definitively removes footnotes.

        TODO: Check if we don't remove too much.

        Args:
            xml: The XML to operate on, as a list of tags.
        """
        most_common_fontsize = self.find_most_common_fontsize(xml)

        # Remove all text nodes whose fontsize is different than most common value.
        for node in xml.find_all('text'):
            if (int(node["fontsize"]) != most_common_fontsize):
                node.extract()
                
    def assert_only_text_nodes_with_most_common_fontsize_left(self, xml):
        """Asserts that all <text> nodes have the most common fontsize.
        
        Args:
            xml: The XML to operate on, as a list of tags.
        """
        most_common_fontsize = self.find_most_common_fontsize(xml)  
        for node in xml.find_all("text"):
            if int(node["fontsize"]) != most_common_fontsize:
                raise Exception("Found <text> node not having most common font size:\n" + str(node))

    def join_text_nodes_on_same_lines(self, xml):
        """Concatenates nodes that are on the same line. Note that this may remove HTML formatting
        inside nodes.

        Args:
            xml: The XML to operate on, as a list of tags.
        """
        last_node = None
        for node in xml.find_all("text"):
            if node.has_attr("line"):
                last_node = node
                break
        for node in xml.find_all("text"):
            if not node.has_attr("line"):
                continue
            if int(node["line"]) > int(last_node["line"]):
                last_node = node
            elif int(node["left"]) > int(last_node["left"]) + int(last_node["width"]):
                last_node.string = last_node.get_text().strip() + " " + node.get_text().strip()
                last_node["width"] = int(last_node["width"]) + int(node["width"])
                node.extract()
    
    def assert_each_text_node_has_increasing_line_attr(self, xml):
        """Asserts that:
        - Each <text> node has a "line" attribute.
        - They are strictly increasing. (This means at most one <text> node per "line" value and
          <text> nodes are sorted by "line" values.)

        Args:
            xml: The XML to operate on, as a list of tags.
        """
        last_line = 0
        for node in xml.find_all("text"):
            if not node.has_attr("line"):
                raise Exception("Missing 'line' attribute:\n" + str(node))
            if int(node["line"]) <= last_line:
                raise Exception("Non-increasing 'line' attribute:\n" + str(node))
            last_line = int(node["line"])

    def add_indent_info_for_dashed_lines(self, xml):
        """Add plaintext indentation prefix to all lines that start with a dash representing
        either a new logical division unit, or a dashed explanatory section for a list preceding it
        (see below).

        "Dashed explanatory section" is easiest understood by example:
        Art. 123 Sausages may be consumed:
        1) cooked, or
        2) grilled, or
        3) fried
        - unless they have been pre-smoked.

        The plaintext info has the form of a prefix "@@INDENT{X}@@", where the bit "{X}" is a
        number 0, 1, 2, 3, .., indicating which indentation level the dashed line starts at.

        Args:
            xml: The XML to operate on, as a list of tags.
        """

        # For each line, add its indent level.
        indent_levels = self.get_all_indent_levels(xml)
        for node in xml.find_all('text'):
            left = int(node["left"])
            indent_level = self.get_indent_level(left, indent_levels)
            if not indent_level is None:
                node["indent"] = indent_level
                node.string = "@@INDENT" + str(indent_level) + "@@" + node.get_text()

        # Check all line starts. If they begin with a dash, and the dash is just in a running
        # piece of text (as opposed to e.g. a list of tirets, or explanatory section at the end
        # of a list of points) - then move the dash to the line above. 
        last_seen_top = 0
        last_line_start = None
        last_node = None
        for node in xml.find_all("text"):
            if (int(node["top"]) > last_seen_top):
                if ((not last_node is None) and (not last_line_start is None) 
                    and self.should_join_dash_line(node, last_node, last_line_start)):
                    # Moving the dash to the line above. Note that one trailing whitespace will be
                    # added after the dash when newlines are removed.
                    last_node.string = last_node.get_text().strip() + u" –"
                    node.string = re.sub(ur"@@– ", "@@", node.get_text().strip(), re.UNICODE)
                last_line_start = node
                last_seen_top = int(node["top"])
            last_node = node

        # Remove indent info for all lines except ones still starting with dash.
        for node in xml.find_all("text"):
            if not re.match(self.DASH_PREFIX_WITH_INDENT, node.get_text()):
                node.string = re.sub(r"^@@INDENT\d@@", "", node.get_text().strip())

    def get_all_indent_levels(self, xml):
        """Returns a list of all indent levels found in the PDF.

        Args:
            xml: The XML to operate on, as a list of tags.

        Returns:
            list: List of indent levels.
        """

        # Get list of indent levels, with corresponding "left" attribute.
        last_seen_top = 0
        lefts = {}
        for node in xml.find_all('text'):
            if (int(node["top"]) <= last_seen_top):
                continue
            last_seen_top = int(node["top"])
            left = int(node["left"])
            lefts[left] = ((lefts[left] + 1) if lefts.has_key(left) else 1)
       
        # Sort by the "left" offset.
        lefts = sorted(lefts.items(), key=lambda x: x[0])        
        # Check which of the two options of indent levels we have.
        lefts = [item[0] for item in lefts]
        if (lefts[0] == 96):
            return self.INDENT_LEVELS1
        if (lefts[0] == 76):
            return self.INDENT_LEVELS2
        return None

    def get_indent_level(self, left, indents):
        """For a given value of "left" parameter of an XML node and list of increasing indent
        levels in a document, returns an indent level which matches the "left" param or None
        if there isn't one. Note that matching has an error threshold of about 13 points - e.g.
        "left" == 123 matches indent level at 125 points. This is because there can be certain
        variation in the PDFs, especially when a law changes another law and the other law is
        quoted. 13 seems right because it's less than half of any interval between indent levels
        (see INDENT_LEVELS1, INDENT_LEVELS2).

        Args:
            left: The value of the "left" attribute (offset from left edge of PDF page).
            indents: One-dimensional increasing list of indent levels found in the PDF.

        Returns:
            int|None: Index of the indent in the list, or None if not found.
        """
        idx = 0
        for indent in indents:
            if ((left - 13) < indent) and ((left + 13) > indent):
                return idx
            idx = idx + 1
        return None
    
    def should_join_dash_line(self, node, last_node, last_line_start):
        """Returns whether text in param node starts with a dash, and if so, whether it should be
        combined with the previous node. This concatenation should take place if the dash doesn't
        represent a new logical division (e.g. tiret), or a dashed section holding a summary for
        a list of items above it, but is simply the continuation of text from previous line.

        Args:
            node: The XML node whose text may need to be joined to previous line.
            last_node: The XML directly preceding this node.
            last_line_start: The node holding the beginning of previous line (which may or
                may not be the same as last_node).

        Returns:
            bool: True if text of node starts with a dash and if so, if it should be glued
                together with previous line.
        """
        if not re.match(self.DASH_PREFIX_WITH_INDENT, node.get_text()):
            return False
        current_indent_level = int(node["indent"])
        last_indent_level = int(last_line_start["indent"])
        last_line = last_line_start.get_text()
        if current_indent_level == 0:
            if (last_indent_level == 0) and (not re.match(self.POINT_PREFIX_WITH_INDENT,last_line)):
                return True
            if (last_indent_level == 1) and (re.match(self.LEVEL0_PREFIX_WITH_INDENT, last_line)):
                return True
        if current_indent_level == 1:
            if (last_indent_level < 2) and (not re.match(self.LETTER_PREFIX_WITH_INDENT,last_line)):
                return True
        if current_indent_level == 2:
            join = True
            if (re.match('.*:\s*$', last_node.get_text())):
                join = False
            if (last_indent_level == 3):
                join = False
            if (last_indent_level == 2) and (re.match(self.DASH_PREFIX_WITH_INDENT, last_line)):
                join = False
            return join
        if current_indent_level == 3:
            return not re.match(self.DOUBLE_TIRET_PREFIX_WITH_INDENT, node.get_text())
        if current_indent_level == 4:
            return not re.match(self.TRIPLE_TIRET_PREFIX_WITH_INDENT, node.get_text())
        return False

    def add_newline_if_level0_unit_starts_with_level1_unit(self, xml):
        """In Polish law, the main logical unit for normative laws is denoted "Art." and
        for executive laws "§". The logical unit one level below, is denoted usually by
        strings matching the regex "\d+[a-z]*\.", and occasionally with "§ " prepended to that.
        (Note that there may also be a superscript before the ending dot.)

        Unlike pretty much all other logical units, if a main unit (which we call level 0)
        immediately starts with a unit one level below (which we call level 1), then the level 1
        unit starts NOT on the next line, but on the same line as the level 0 heading. For example,
        we might get the following plain text after parsing the PDF (note the lack of "\n" between
        "Art. 123." and following "1."): "Art. 123. 1. Some text. \n 2. Some more text."

        Such cases are difficult for the parser to tell apart from level 0 units which only
        have a single body of text (not divided into level 1 units) - they start on the same line
        too. To make it easier to distinguish them, we detect here the cases of a level 1 unit
        starting on the same line as level 0 unit, and add a newline between them.
        """

        regex = ( ur"^(" + self.LEVEL0_PREFIX_REGEX + ur")" + ur"\s+"
                 + ur"(" + self.LEVEL1_PREFIX_REGEX + ur")")
        for node in xml.find_all('text'):
            node.string = re.sub(regex, ur"\g<1>\n\g<2>", node.get_text())
            
    def xml_to_text(self, xml):
        """Convert the Beautiful Soup XML into plain text. I'm not using xml.get_text() because
        it can glue <text> tags together without either whitespace or newline between them. 

        Args:
            xml: The XML to operate on, as a list of tags.

        Returns:
            str: The law plain text.
        """
        result = ""
        for node in xml.find_all("text"):
            result = result + node.get_text().strip() + "\n"
        return result

    def join_hyphenated_words(self, text):
        """ Join hyphenated words - ones that have been split in middle b/c of line end.

        Args:
            text (str): The law text.

        Returns:
            str: The law text after processing.
        """
        return re.sub(ur"([a-ząćęłńśóźż])-\n([a-ząćęłńśóźż])", "\g<1>\g<2>", text)

    def remove_linebreaks(self, text):
        """ Remove all line breaks, except when the new line starts with a symbol known
        to be the start of a division or a dashed section (starting with @@INDENT).

        Args:
            text (str): The law text.

        Returns:
            str: The law text with line breaks removed.
        """
        return re.sub(ur"\n(?!("
                      u"KSIĘGA\s+(PIERWSZA|DRUGA|TRZECIA|CZWARTA|PIĄTA|SZÓSTA|SIÓDMA|ÓSMA)|"
                      u"TYTUŁ\s+[IVXLC]|"
                      u"DZIAŁ\s+[IVXLC]|"
                      u"Rozdział\s+[IVXLC1-9]|"
                      u"Art\.|"
                      u"§\s+\d+[a-z]*\.|"
                      u"\d+[a-z]*\.|"
                      u"\d+[a-z]*\)|"
                      u"[a-z]+\)|"
                      u"@@INDENT))", " ", text)

    def trim_lines(self, text):
        """Remove leading and trailing whitespace from all the lines in the text.

        Args:
            text (str): The law text.

        Returns:
            str: The law text with each line trimmed.
        """
        result = ""
        for line in text.splitlines():
            result = result + line.strip() + "\n"
        return result
