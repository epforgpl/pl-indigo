# -*- coding: utf-8 -*-
import re

from bs4 import BeautifulSoup
from indigo_api.importers.base import Importer
from indigo.plugins import plugins


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

    SUPERSCRIPT_START = "@@SUPERSCRIPT@@"
    """Special label placed in law plaintext before a superscript string."""

    SUPERSCRIPT_END = "##SUPERSCRIPT##"
    """Special label placed in law plaintext after a superscript string."""

    HEADER_END_OFFSET = 50
    """How far from top of page we assume header is over."""

    FOOTER_START_OFFSET = 1060
    """How far from top of page we assume footer is starting."""

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

    INDENT_LEVEL_FREQUENCY_THRESHOLD = 5
    """How many times a given indentation must occur in PDF so that we assume it's one of the
    indentation levels, and not just a bit of text that for whatever reason PDF separated out
    into its own <text> tag. Example when this may happen is a line like this:
    "This is an important law <this is in superscript>3)</this is in superscript>, which..."
    Because of the fact that the string '3)' is in superscript (a footnote), the text on this
    line is broken into three <text> tags: one containing "This is an important law", second "3)",
    third ", which...". We don't want the start of ", which..." to be counted as an indentation
    level.
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
        self.remove_header_and_footer(xml)
        self.process_superscripts(xml)
        self.remove_footnotes(xml)
        self.add_indent_info_for_dashed_lines(xml)
        self.add_newline_if_level0_unit_starts_with_level1_unit(xml)
        text = xml.get_text() # Strip XML tags.
        text = self.join_hyphenated_words(text)
        text = self.remove_linebreaks(text)
        return text

    def remove_header_and_footer(self, xml):
        """Modify the passed in XML by removing tags laying outside the area we know to be
        the actual law text. Generally, this will be the ISAP header, and footer containing 
        page numbers.

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
        return ((tag.name == "text") and tag.has_attr("top")
            and ((int(tag["top"]) <= self.HEADER_END_OFFSET) 
                 or (int(tag["top"]) > self.FOOTER_START_OFFSET)))

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

            node_txt = node.get_text()
            node_plus_one_txt = node_plus_one.get_text()
            node_plus_two_txt = node_plus_two.get_text()

            if not superscript_pattern.match(node_plus_one_txt):
                continue

            if not node_plus_two_pattern.match(node_plus_two_txt):
                continue

            if ((not node.has_attr("height")) or (not node_plus_one.has_attr("height"))
                    or (not node_plus_two.has_attr("height")) or (not node.has_attr("top"))
                    or (not node_plus_one.has_attr("top")) or (not node_plus_two.has_attr("top"))):
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
        """Modify the passed in XML by searching for tags which have smaller font ("height"
        attribute) than most tags in the document. Remove all such tags. This definitively
        removes footnotes.

        TODO: Check if we don't remove too much.

        Args:
            xml: The XML to operate on, as a list of tags.
        """
        text_nodes = xml.find_all('text')

        # Find the most commonly occurring height of text nodes. We'll assume this is
        # the height of the law text itself.
        heights = {}
        for node in text_nodes:
            if not node.has_attr("height"):
                continue
            height = int(node["height"])
            heights[height] = ((heights[height] + 1) if heights.has_key(height) else 1)
        most_common_height = max(heights, key = heights.get)

        # Remove all text nodes whose height is lower than most_common_height.
        for node in text_nodes:
            if node.has_attr("height") and (int(node["height"]) < most_common_height):
                node.extract()

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

        # Increase "top" attribute by 10000 for each page. Then it's monotonically increasing.
        page_nodes = xml.find_all("page")
        for page in page_nodes:
            num = int(page["number"])
            text_nodes = page.find_all("text")
            for node in text_nodes:
                if not node.has_attr("top"):
                    continue
                node["top"] = int(node["top"]) + 10000 * num

        # For each line, add its indent level.
        indent_levels = self.get_all_indent_levels(xml)
        text_nodes = xml.find_all('text')
        for node in text_nodes:
            left = int(node["left"])
            indent_level = self.get_indent_level(left, indent_levels)
            if not indent_level is None:
                node["indent"] = indent_level
                node.string = "@@INDENT" + str(indent_level) + "@@" + node.get_text()

        # Check all line starts. If they begin with a dash, and the dash is just in a running
        # piece of text (as opposed to e.g. a list of tirets, or explanatory section at the end
        # of a list of points) - then move the dash to the line above.
        text_nodes = xml.find_all("text")
        last_seen_top = 0
        last_line_start = None
        last_node = None
        for node in text_nodes:
            if node.has_attr("top") and (int(node["top"]) > last_seen_top):
                if ((not last_node is None) and (not last_line_start is None) 
                    and self.should_join_dash_line(node, last_node, last_line_start)):
                    # Moving the dash to the line above. Note that one trailing whitespace will be
                    # added after the dash when newlines are removed.
                    last_node.string = last_node.get_text() + u" –"
                    node.string = re.sub(ur"@@– ", "@@", node.get_text(), re.UNICODE)
                last_line_start = node
                last_seen_top = int(node["top"])
            last_node = node

        # Remove indent info for all lines except ones still starting with dash.
        text_nodes = xml.find_all("text")
        for node in text_nodes:
            if not re.match(self.DASH_PREFIX_WITH_INDENT, node.get_text()):
                node.string = re.sub(r"^@@INDENT\d@@", "", node.get_text())

    def get_all_indent_levels(self, xml):
        """Returns a list of all indent levels found in the PDF at least on 5 text nodes,
        with ascending sort.

        Args:
            xml: The XML to operate on, as a list of tags.

        Returns:
            list: List of indent levels.
        """

        # Get list of indent levels, with corresponding "left" attribute.
        last_seen_top = 0
        lefts = {}
        for node in xml.find_all('text'):
            if not node.has_attr("top") or (int(node["top"]) <= last_seen_top):
                continue
            last_seen_top = int(node["top"])
            left = int(node["left"])
            lefts[left] = ((lefts[left] + 1) if lefts.has_key(left) else 1)

        # Filter out values found less than 5 times (hopefully that's a good number?)
        lefts = {k: v for k, v in lefts.items() if v >= self.INDENT_LEVEL_FREQUENCY_THRESHOLD}        
        # Sort by the "left" offset.
        lefts = sorted(lefts.items(), key=lambda x: x[0])
        # Return one-dimensional list of "left" attribute values for each indent level.
        return [item[0] for item in lefts]

    def get_indent_level(self, left, indents):
        """For a given value of "left" parameter of an XML node and list of increasing indent
        levels in a document, returns an indent level which matches the "left" param or None
        if there isn't one. Note that matching has an error threshold of about 3 points - e.g.
        "left" == 123 matches indent level at 125 points.

        Args:
            left: The value of the "left" attribute (offset from left edge of PDF page).
            indents: One-dimensional increasing list of indent levels found in the PDF.

        Returns:
            int|None: Index of the indent in the list, or None if not found.
        """
        idx = 0
        for indent in indents:
            if ((left - 3) < indent) and ((left + 3) > indent):
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
            if (re.match('.*:$', last_node.get_text())):
                join = False
            if (last_indent_level == 3):
                join = False
            if (last_indent_level == 2) and (re.match(self.DASH_PREFIX_WITH_INDENT, last_line)):
                join = False
            return join
        # TODO: Add indent levels higher than 2.
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
