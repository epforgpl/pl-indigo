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

    NO_HEIGHT = -1
    """Magic number to indicate that we couldn't find height for the node that has it."""
    
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

    LEVEL0_PREFIX_REGEX = (ur"(?:Art.|§)\s+\d+[a-ząćęłńóśźż]*"
                           ur"(?:@@SUPERSCRIPT@@[^#]+##SUPERSCRIPT##)?\.")
    """Regex catching line starts for level 0 law hierarchy units."""

    LEVEL1_PREFIX_REGEX = (ur"(?:§\s+)?\d+[a-ząćęłńóśźż]*"
                           ur"(?:@@SUPERSCRIPT@@[^#]+##SUPERSCRIPT##)?\.")
    """Regex catching line starts for level 1 law hierarchy units."""

    INDENT_REGEX = ur"^@@INDENT\d@@"
    """Regex catching lines starting with indent mark."""

    LEVEL0_PREFIX_WITH_INDENT = INDENT_REGEX + LEVEL0_PREFIX_REGEX
    """Regex catching line starts for level 0 law hierarchy units, with indent info prepended."""

    POINT_PREFIX_WITH_INDENT = INDENT_REGEX + (ur"\d+[a-ząćęłńóśźż]*" 
                                               ur"(@@SUPERSCRIPT@@[^#]+##SUPERSCRIPT##)?\) ")
    """Regex catching line starts for "point" law hierarchy units, with indent info prepended."""

    LETTER_PREFIX_WITH_INDENT = INDENT_REGEX + (ur"[a-ząćęłńóśźż]+"
                                                ur"(@@SUPERSCRIPT@@[^#]+##SUPERSCRIPT##)?\) ")
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
    INDENT_LEVELS2 = [76, 111, 143, 170, 197]
    """The other option for indent levels in unified Polish law PDFs.

    Getting these numbers from statute: "o odnawialnych źródłach energii".
    http://isap.sejm.gov.pl/isap.nsf/download.xsp/WDU20150000478/U/D20150478Lj.pdf
    
    And from "o systemie oświaty".
    http://isap.sejm.gov.pl/isap.nsf/download.xsp/WDU19910950425/U/D19910425Lj.pdf    
    """

    INDENT_LEVELS3 = [80, 115, 147, 174]
    """Yet another other option for indent levels in unified Polish law PDFs.

    Getting these numbers from statute: "Prawo geodezyjne i kartograficzne".
    http://isap.sejm.gov.pl/isap.nsf/download.xsp/WDU19890300163/U/D19890163Lj.pdf
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
        text = self.remove_outgoing_and_upcoming_section_markers(text)
        xml = BeautifulSoup(text)
        self.assert_all_text_nodes_have_top_left_height_font_attrs(xml)
        self.remove_empty_text_nodes(xml)
        self.remove_header_and_footer(xml)
        self.remove_right_margin(xml)
        self.add_fontsize_to_all_text_nodes(xml)
        self.remove_formulas(xml)
        self.make_top_attribute_monotonically_increasing(xml)
        self.add_line_nums_to_law_text(xml)
        # At this point, all <text> nodes with most common "fontsize" have "line" attribute.
        self.process_superscripts(xml)
        self.remove_footnotes(xml)
        # Commented out because it's too hard parse outgoing and upcoming sections for now.
        # Instead of this, remove_outgoing_and_upcoming_section_markers() was added.
        # self.undecorate_outgoing_and_upcoming_sections(xml)
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

    def remove_outgoing_and_upcoming_section_markers(self, text):
        """Outgoing sections are indicated like this:
        <i>[Art. 123 This is about to stop being in force.]</i>

        Upcoming sections are indicated like this:
        <b>&lt;Art. 123 This is about to start being in force.&gt;</b>

        Ideally, we could parse them as such, match them to the marginal notes saying when
        they go out / come in, and leave the correct ones.

        For now, we just make the resulting text contain both and rely on manual law editors
        to select the right version.

        I previously tried to go in the direction of parsing them more, in the now commented-out
        method undecorate_outgoing_and_upcoming_sections().

        Args:
            text (str): The law text.

        Returns:
            str: The law text after processing.
        """

        # Each block has version with whitespace & without.
        text = re.sub(r"<i>\s+\[", " ", text)
        text = re.sub(r"<i>\[", "", text)

        text = re.sub(r"\]\s+</i>", " ", text)
        text = re.sub(r"\]</i>", "", text)

        text = re.sub(r"<b>\s+&lt;", " ", text)
        text = re.sub(r"<b>&lt;", "", text)

        text = re.sub(r"&gt;\s+</b>", " ", text)
        text = re.sub(r"&gt;</b>", "", text)

        text = re.sub(r"<i>|</i>|<b>|</b>", "", text)
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

    def remove_formulas(self, xml):
        """Remove <text> nodes which draw a mathematical formula. We can't parse them at the
        moment. :(

        Args:
            xml: The XML to operate on, as a list of tags.
        """
        formula_nodes = []
        is_in_formula = False
        previous_node_text = u""
        for node in xml.find_all(name = "text",
                                 attrs = {"fontsize": self.find_most_common_fontsize(xml)}):            
            node_text = node.get_text().strip().replace("  ", " ")
            # Here is how we catch beginning of formula. Add other phrases if needed.
            # We unfortunately may need to look at previous line, hence the nested ifs...
            if (node_text.endswith(u"wzoru:")):
                # Check phrase "według wzoru:".
                if (node_text.endswith(u"według wzoru:")):
                    is_in_formula = True
                elif (previous_node_text.endswith(u"według")):
                    is_in_formula = True
                # Check phrase "według następującego wzoru:".
                if (node_text.endswith(u"następującego wzoru:")):
                    if (node_text.endswith(u"według następującego wzoru:")):
                        is_in_formula = True
                    elif (previous_node_text.endswith(u"według")):
                        is_in_formula = True
                elif (previous_node_text.endswith(u"według następującego")):
                    is_in_formula = True
            elif (is_in_formula):
                # Here is how we catch end of formula. Add other phrases if needed.
                if (node_text.startswith(u"w którym poszczególne symbole oznaczają")
                    or node_text.startswith(u"gdzie poszczególne symbole oznaczają")
                    or node_text.startswith(u"w którym poszczególne litery oznaczają")
                    or node_text.startswith(u"gdzie znaczenie poszczególnych symboli jest następujące")
                    or node_text.startswith(u"gdzie współczynnik")
                    or node_text.startswith(u"gdzie:")):
                    is_in_formula = False
                    # Remove formula nodes.
                    for formula_node in formula_nodes:
                        formula_node.extract()
                else:
                    formula_nodes.append(node)
            previous_node_text = node_text
        if (is_in_formula):
            raise Exception('After iterating through entire law text, parser is inside a formula.')

    def make_top_attribute_monotonically_increasing(self, xml):
        """Increase "top" attribute of <text> nodes by
        {page number <text> is on} * PAGE_NUM_MULTIPLIER.

        Also, call the method balancing out "top" and "height".

        Then, "top" should be monotonically increasing.

        Args:
            xml: The XML to operate on, as a list of tags.
        """
        for page in xml.find_all("page"):
            num = int(page["number"])
            for node in page.find_all("text"):
                node["top"] = int(node["top"]) + self.PAGE_NUM_MULTIPLIER * num
        self.adjust_top_and_height(xml)

    def adjust_top_and_height(self, xml):
        """For whatever reason, sometimes we encounter the following sequence of <text> nodes:
        
        <text .. fontsize="14" height="18" left="111" top="14200208">
          <b>w którym poszczególne symbole oznaczają: </b>
        </text>
        <text .. fontsize="14" height="15" left="111" top="14200239">
          <b>Wk –  wynik końcowy z egzaminów zawodowych, </b>
        </text>
        <text .. fontsize="14" height="15" left="111" top="14200267">
          <b>Kn – </b>
        </text>
        <text .. fontsize="14" height="15" left="164" top="14200267">
          <b>wynik  z egzaminu  zawodowego  z kwalifikacji  wyodrębnionej </b>
        </text>
        <text .. fontsize="14" height="15" left="164" top="14200295">
          <b>w zawodzie, </b></text>
        <text .. fontsize="14" height="15" left="111" top="14200323">
          <b>n – </b>
        </text>
        <text .. fontsize="14" height="18" left="164" top="14200320">
          <b>liczba kwalifikacji wyodrębnionych w danym zawodzie. </b>
        </text>
        
        Note here that all the nodes have the same font size, but "height" differs between
        18 (most common value in ISAP unified texts) and 15 or 16. And in particular, the last two
        nodes in the PDF are visually on the same line, but because of unequal "height" (2-3 point
        difference), the "top" param is also offset by 2-3 points. This in turn causes an exception
        in the code that checks that "top" is monotonically increasing.
        
        So, this method looks for nodes where height is equal "most_common_height - 3" (or 2) and:
        - increases "height" by 2-3
        - decreases "top" by 3.         

        Args:
            xml: The XML to operate on, as a list of tags.
        """
        most_common_height = self.find_most_common_height(xml)
        for node in xml.find_all(name = "text",
                         attrs = {"fontsize": self.find_most_common_fontsize(xml)}):
            if (int(node["height"]) == most_common_height - 2):
                node["height"] = most_common_height
                node["top"] = int(node["top"]) - 2
            if (int(node["height"]) == most_common_height - 3):
                node["height"] = most_common_height
                node["top"] = int(node["top"]) - 3

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
    
    def find_most_common_height(self, xml):
        """Returns the height value that most of <text> nodes in the doc have.

        Args:
            xml: The XML to operate on, as a list of tags.

        Returns:
            int: The height value that most of <text> nodes have.
        """
        heights = {}
        for node in xml.find_all("text"):
            height = int(node["height"])
            heights[height] = ((heights[height] + 1) if heights.has_key(height) else 1)
        most_common_height = max(heights, key = heights.get)
        if (most_common_height == self.NO_HEIGHT):
            raise Exception("Most common height in the PDF can't be the marker for no height.")
        return most_common_height

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

    # Commented out because it's too hard parse outgoing and upcoming sections for now.
    # Instead of this, remove_outgoing_and_upcoming_section_markers() was added.
    """
    def undecorate_outgoing_and_upcoming_sections(self, xml):
        In ISAP unified texts, when a given article, etc is changing on some future date, they
        first print the current version in italics and inside '[ ... ]' markers, and immediately
        after, they print the upcoming version in bold and inside '< ... >' markers.

        This function removes the '[', ']', '<', '>' markers. We rely on the person doing manual
        post-processing to remove the section that's currently not effective and leave the section
        that's currently in force.

        Note that we don't currently catch cases when the outgoing/upcoming sections happen inline,
        for example like this: "2) w okresie między dniem 1 stycznia następnego roku 
        a [terminem określonym dla złożenia] <upływem terminu określonego na złożenie> zeznania..".
        
        Examples of situations this has to deal with (all are checked in test_importer_pl.py):
        
        1. Ustawa z dnia 12 października 1990 r. o Straży Granicznej
           Art. 5aa is coming into force
           Note here the line with *2* <b> markers (starts "podległych ...").
           
        <text ...>3)  BSWSG wykonuje Komendant BSWSG. </text> # This is end of previous unit.
        <text ...><b>&lt;Art. 5aa. 1.  Komendant  Główny  Straży  Granicznej  może  upoważnić </b></text>
        <text ...><b>podległych  funkcjonariuszy  lub  pracowników  do  załatwiania</b> <b>spraw  w jego </b></text>
        <text ...><b>imieniu w określonym zakresie. </b></text>
        <text ...><b>2. Komendant  oddziału  Straży  Granicznej  może  upoważnić  podległych </b></text>
        <text ...><b>funkcjonariuszy  pełniących  służbę  w terytorialnym  zasięgu  działania  oddziału </b></text>
        <text ...><b>lub pracowników do załatwiania spraw w jego imieniu w określonym zakresie. </b></text>
        <text ...><b>3. Upoważnienia,  o których  mowa  w ust. 1  i 2,  mogą  być  udzielone,  jeżeli </b></text>
        <text ...><b>zakres  danego  upoważnienia  nie  został  określony  w ustawie  albo  w przepisach </b></text>
        <text ...><b>wydanych na podstawie ustawy.&gt;</b> </text>
        <text ...><b>Art. 5b.</b> Kierownicy ... </text> # This is start of next unit.
        
        2. Ustawa z dnia 12 października 1990 r. o Straży Granicznej
           Old version of Art. 16g is being retired.
           Note here <b></b> inside <i></i>.
        
        <text ...><i>zezwolenia ... ostateczna.] </i></text> # This is end of previous unit.
        <text ...><i>[<b>Art. 16g.</b></i></text>
        <text ...><i>1.  Organy  administracji  miar  są  uprawnione  do  przeprowadzania </i></text>
        <text ...><i>kontroli  podmiotów  i przedsiębiorców,  o których  mowa  w art. 16a  i art. 16c, </i></text>
        <text ...><i>w zakresie  spełniania  warunków  niezbędnych  do  wykonywania  udzielonych </i></text>
        <text ...><i>upoważnień i zezwoleń oraz przestrzegania przepisów ustawy. </i></text>
        <text ...><i>2. Do  kontroli  upoważnionych  podmiotów  i uprawnionych  przedsiębiorców </i></text>
        <text ...><i>stosuje się odpowiednio przepisy art. 21 ust. 1 pkt 1 i 4, ust. 2 i 4.] </i></text>
        <text ...><b>&lt;Art. 16g. Organy ... </b></text> # This is start of next unit.
        
        3. Ustawa z dnia 27 sierpnia 2004 r. o świadczeniach opieki zdrowotnej finansowanych 
           ze środków publicznych
           Art. 20, ust. 1 is changing
           Note here that in one <text> node we have <b>Art. 20.</b> and <i>...</i>.
        
        <text ...><b>przepisy ... &gt; </b></text> # This is end of previous unit.
        <text ...><b>Art. 20.</b> <i>[1.  Świadczenia  opieki  zdrowotnej  w szpitalach  i świadczenia </i></text>
        <text ...><i>specjalistyczne w ambulatoryjnej opiece zdrowotnej są udzielane według kolejności </i></text>
        <text ...><i>zgłoszenia  w dniach  i godzinach  ich  udzielania  przez  świadczeniodawcę,  który </i></text>
        <text ...><i>zawarł umowę o udzielanie świadczeń opieki zdrowotnej.]</i> </text>
        <text ...><b>&lt;1. Świadczenia </b></text>
        <text ...><b>opieki </b></text>
        <text ...><b>zdrowotnej </b></text>
        <text ...><b>w szpitalach, </b></text>
        <text ...><b>świadczenia </b></text>
        <text ...><b>specjalistyczne  w ambulatoryjnej  opiece  zdrowotnej  oraz  stacjonarne </b></text>
        <text ...><b>i całodobowe  świadczenia  zdrowotne  inne  niż  szpitalne  są  udzielane  według </b></text>
        <text ...><b>kolejności  zgłoszenia  w dniach  i godzinach  ich  udzielania  przez </b></text>
        <text ...><b>świadczeniodawcę,  który  zawarł  umowę  o udzielanie  świadczeń  opieki </b></text>
        <text ...><b>zdrowotnej.&gt; </b></text>
        <text ...>1a. Na  liście  ... </text> # This is start of next unit.
        
        4. Ustawa z dnia 15 lipca 2011 r. o zawodach pielęgniarki i położnej
           In Art. 80, ust 8, pkt 1 a few words inside a sentence are changing.
        
        <text ...>8. Potwierdzenia, o którym mowa w ust. 7, dokonuje się na podstawie wniosku </text>
        <text ...>o nadanie uprawnień: </text>
        <text ...>1)  podpisanego  kwalifikowanym  podpisem  elektronicznym  <i>[lub  podpisem </i></text>
        <text ...><i>zaufanym]</i> <b>&lt;podpisem zaufanym lub podpisem osobistym&gt;</b> lub </text>
        <text ...>2)  potwierdzonego  przez  właściwą  okręgową  izbę  pielęgniarek  i  położnych  lub </text>
        <text ...>Naczelną  Izbę  Pielęgniarek  i  Położnych  w  zakresie  danych  podmiotu </text>
        <text ...>zamierzającego wykonywać działalność w zakresie kształcenia podyplomowego, </text>
        <text ...>o którym mowa w ust. 1. </text>
        
        5. Ustawa z dnia 16 lipca 2004 r. Prawo telekomunikacyjne
        
        <text ...><b>Art. 61a.</b> <i>[1. Jeżeli konieczność wprowadzenia zmiany warunków umowy, w tym </i></text>
        <text ...><i>określonych </i></text>
        <text ...><i>w regulaminie </i></text>
        <text ...><i>świadczenia </i></text>
        <text ...><i>publicznie </i></text>
        <text ...><i>dostępnych </i></text>
        <text ...><i>usług </i></text>
        <text ...><i>telekomunikacyjnych lub w cenniku usług telekomunikacyjnych, wynika wyłącznie ze </i></text>
        <text ...><i>zmiany stawki podatku od towarów i usług stosowanej dla usług telekomunikacyjnych, </i></text>
        <text ...><i>dostawca  publicznie  dostępnych  usług  telekomunikacyjnych  wykonuje  obowiązki, </i></text>
        <text ...><i>o których  mowa  w art. 60a  ust. 1  i 1b  oraz  art. 61  ust. 5  i 5a,  poprzez  podanie  do </i></text>
        <text ...><i>publicznej  wiadomości  informacji:]</i> <b>&lt;Jeżeli  konieczność  wprowadzenia  zmiany </b></text>
        <text ...><b>warunków  umowy,  w tym  określonych  w regulaminie  świadczenia  publicznie </b></text>
        <text ...><b>dostępnych </b></text>
        <text ...><b>usług </b></text>
        <text ...><b>telekomunikacyjnych </b></text>
        <text ...><b>lub </b></text>
        <text ...><b>w cenniku </b></text>
        <text ...><b>usług </b></text>
        <text ...><b>telekomunikacyjnych, wynika wyłącznie ze zmiany stawki podatku od towarów </b></text>
        <text ...><b>i usług  stosowanej  dla  usług  telekomunikacyjnych,  dostawca  publicznie </b></text>
        <text ...><b>dostępnych  usług  telekomunikacyjnych  wykonuje  obowiązki,  o których  mowa </b></text>
        <text ...><b>w art. 60a ust. 1 i 1b oraz art. 61 ust. 5 i 5a, przez publikację na swojej stronie </b></text>
        <text ...><b>internetowej informacji:&gt;</b> </text>
        <text ...>1)  o  zmianie  warunków  umowy,  w tym  określonych  w regulaminie  świadczenia </text>
        <text ...>publicznie  dostępnych  usług  telekomunikacyjnych,  zmianie  w cenniku  usług </text>
        <text ...>telekomunikacyjnych, terminie ich wprowadzenia, wraz ze wskazaniem miejsca </text>
        <text ...>udostępnienia  treści  zmiany  lub  warunków  umowy  lub  cennika </text>
        <text ...>uwzględniających tę zmianę; </text>
        <text ...>2)  o prawie wypowiedzenia umowy przez abonenta w przypadku braku akceptacji </text>
        <text ...>tych zmian; </text>

        6. Ustawa z dnia 25 sierpnia 2006 r. o biokomponentach i biopaliwach ciekłych (Art. 23)
        Note how someone at ISAP excluded ".&gt;" from <b></b>.

        <text ...>ciekłych i biopaliw ciekłych. </text> # This is end of previous unit.
        <text ...><b>&lt;1d.  Podmiot  realizujący  Narodowy  Cel  Wskaźnikowy  może  zrealizować </b></text>
        <text ...><b>obowiązek,  o którym  mowa  w ust. 1,  z wykorzystaniem  biokomponentów </b></text>
        <text ...><b>zawartych w paliwach powstałych w wyniku współuwodornienia. </b></text>
        <text ...><b>1e. Minister właściwy do spraw energii określi, w drodze rozporządzenia, </b></text>
        <text ...><b>metodykę  obliczania  zawartości  biokomponentów  zawartych  w paliwach </b></text>
        <text ...><b>powstałych  w wyniku  współuwodornienia,  biorąc  pod  uwagę  stan  wiedzy </b></text>
        <text ...><b>technicznej  w tym  zakresie  wynikający  z badań  tych  paliw  lub  doświadczenia </b></text>
        <text ...><b>w ich stosowaniu</b>.&gt;<b> </b></text>
        <text ...>2. Minimalny udział, o którym mowa w ust. 1: </text> # This is start of next unit.

        Args:
            xml: The XML to operate on, as a list of tags.


        is_in_outgoing_part = False
        is_in_upcoming_part = False
        for node in xml.find_all('text'):
            i_tags = node.find_all('i') # Find italics.
            b_tags = node.find_all('b') # Find bold.

            # Get the following texts without any tags, with and without whitespaces:
            # (1) entire text in the node,
            # (2) concatenated text pieces in all <i> tags,
            # (3) concatenated text pieces in all <b> tags.
            text = node.get_text().strip()
            text_no_whitespace = node.get_text().replace(" ", "")
            itext_no_whitespace = ""
            itext = ""
            for i_tag in i_tags:
                itext_no_whitespace = itext_no_whitespace + i_tag.get_text().replace(" ", "")
                itext = itext + i_tag.get_text().strip()
            btext_no_whitespace = ""
            btext = ""
            for b_tag in b_tags:
                btext_no_whitespace = btext_no_whitespace + b_tag.get_text().replace(" ", "")
                btext = btext + b_tag.get_text().strip()

            if (is_in_outgoing_part and is_in_upcoming_part):
                raise Exception("Impossible to be in outgoing and upcoming section at same time.")
            elif (is_in_outgoing_part and not is_in_upcoming_part):
                # For a line fully belonging to an outgoing section.
                if (itext_no_whitespace == text_no_whitespace):
                    if text.endswith("]"):
                        is_in_outgoing_part = False
                        node.string = text.rstrip("]")
                # For a line combining outgoing section and upcoming section (see the method
                # comment, example from "Ustawa z dnia 16 lipca 2004 r. Prawo telekomunikacyjne").
                elif ((itext_no_whitespace + btext_no_whitespace == text_no_whitespace) 
                      and itext.endswith("]") and btext.startswith("<")):
                    is_in_outgoing_part = False
                    node.string = itext.rstrip("]") + u" " + btext.lstrip("<").rstrip(">")
                    if not btext.endswith(">"): # Needed in case upcoming section is one line only.
                        is_in_upcoming_part = True
                else:
                    raise Exception("Expected italics while being in outgoing section.")
            elif (not is_in_outgoing_part and is_in_upcoming_part):
                if ((btext_no_whitespace == text_no_whitespace)
                    # In case someone excludes ".&gt;" from <b></b> markers.
                    or (btext_no_whitespace + u".>") == text_no_whitespace):                    
                    if text.endswith(">"):
                        is_in_upcoming_part = False
                        node.string = text.rstrip(">")
                else:
                    raise Exception("Expected bold while being in upcoming section.")
            else:
                if (itext_no_whitespace == text_no_whitespace) and text.startswith("["):
                    node.string = text.lstrip("[").rstrip("]")
                    if not text.endswith("]"): # Needed in case outgoing section is one line only.
                        is_in_outgoing_part = True
                elif (btext_no_whitespace == text_no_whitespace) and text.startswith("<"):
                    node.string = text.lstrip("<").rstrip(">")
                    if not text.endswith(">"): # Needed in case upcoming section is one line only.
                        is_in_upcoming_part = True
                # For cases like: "<text ...><b>Art. 22c.</b> <i>[1. Some text </i></text>."
                elif ((btext_no_whitespace + itext_no_whitespace == text_no_whitespace)
                    and btext.startswith("Art.") and itext.startswith("[")):
                    node.string = btext + u" " + itext.lstrip("[").rstrip("]")
                    if not itext.endswith("]"): # Needed in case outgoing section is one line only.
                        is_in_outgoing_part = True
    """

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
                node.string = "@@INDENT" + str(indent_level) + "@@" + node.get_text().strip()

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
        if (lefts[0] == 80):
            return self.INDENT_LEVELS3
        raise Exception('Could not match any indent level set to the document.')

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
        last_line = last_line_start.get_text().strip()
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
            node.string = re.sub(regex, ur"\g<1>\n\g<2>", node.get_text().strip())
            
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
                      u"CZĘŚĆ\s+(OGÓLNA|SZCZEGÓLNA|WOJSKOWA)|"
                      u"KSIĘGA\s+(PIERWSZA|DRUGA|TRZECIA|CZWARTA|PIĄTA|SZÓSTA|SIÓDMA|ÓSMA)|"
                      u"TYTUŁ\s+[IVXLC]|"
                      u"DZIAŁ\s+[IVXLC]|"
                      u"Rozdział\s+[IVXLC1-9]|"
                      u"Oddział\s+[IVXLC1-9]|"
                      u"Art\.|"
                      u"§\s+\d+[a-ząćęłńśóźż]*(?:@@SUPERSCRIPT@@[^#]+##SUPERSCRIPT##)?\.|"
                      u"\d+[a-ząćęłńśóźż]*(?:@@SUPERSCRIPT@@[^#]+##SUPERSCRIPT##)?\.|"
                      u"\d+[a-ząćęłńśóźż]*\)|"
                      u"[a-ząćęłńśóźż]+\)|"
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
