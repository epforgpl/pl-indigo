# -*- coding: utf-8 -*-

from nose.tools import *  # noqa

from bs4 import BeautifulSoup
from django.test import testcases
from indigo_pl.importer import ImporterPL

def make_tag(text, top = 100, left = ImporterPL.INDENT_LEVELS1[0], height = 18, font = 1):
    return (u"<text top='" + utfify(top) 
            + u"' left='" + utfify(left) 
            + u"' height='" + utfify(height)
            + u"' width='10" 
            + u"' font='" + utfify(font) + u"'>" + text + u"</text>")
    
def make_fontspec_tag(font_id = 1, size = 18):
    return (u"<fontspec id='" + utfify(font_id) 
            + u"' size='" + utfify(size) + u"'></fontspec>")

def utfify(num):
    return str(num).encode("utf-8").decode("utf-8")

def assertEquals(computed, expected, msg = None):
    try:
        assert_equals(computed, expected, msg)
    except AssertionError:
        raise AssertionError("Values are not equal.\n\n\nCOMPUTED:\n[" 
                             + computed + "]\n\n" + "EXPECTED:\n[" + expected + "]\n")

class ImporterPLTestCase(testcases.TestCase):

    def setUp(self):
        self.importer = ImporterPL()

    def test_reformat_text_simple(self):
        line1 = u"All your base are belong"
        line2 = u"to Legia Warszawa FC."
        reformatted = self.importer.reformat_text(u""
            + make_tag(line1, top = 100) + u"\n" 
            + make_tag(line2, top = 110)
            + make_fontspec_tag())
        assertEquals(reformatted, "All your base are belong to Legia Warszawa FC.\n")
        
    def test_reformat_text_remove_empty_tag(self):
        line1 = u"All your base are belong to Legia Warszawa FC."
        line2 = u"      "
        reformatted = self.importer.reformat_text(u"" 
            + make_tag(line1, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n" 
            + make_tag(line2, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_fontspec_tag())
        assertEquals(reformatted, "All your base are belong to Legia Warszawa FC.\n")

    def test_reformat_text_add_fontsize(self):
        line1 = u"All your base are belong to Legia Warszawa FC."
        line2 = u"The right to consume sausages shall not be abrogated."
        text = (make_tag(line1, font = 1) + u"\n" + make_tag(line2, font = 2) 
                + make_fontspec_tag(font_id = 1, size = 123) 
                + make_fontspec_tag(font_id = 2, size = 456))
        xml = BeautifulSoup(text)
        self.importer.add_fontsize_to_all_text_nodes(xml)
        assertEquals(xml.prettify(), '' 
                    + '<html>\n'
                    + ' <body>\n'
                    + '  <text font="1" fontsize="123" height="18" left="96" top="100" width="10">\n'
                    + '   All your base are belong to Legia Warszawa FC.\n'
                    + '  </text>\n'
                    + '  <text font="2" fontsize="456" height="18" left="96" top="100" width="10">\n'
                    + '   The right to consume sausages shall not be abrogated.\n'
                    + '  </text>\n'
                    + '  <fontspec id="1" size="123">\n'
                    + '  </fontspec>\n'
                    + '  <fontspec id="2" size="456">\n'
                    + '  </fontspec>\n'
                    + ' </body>\n'
                    + '</html>')
        
    def test_undecorate_outgoing_and_upcoming_sections(self):
        line1 = u"<i>[All your base</i>"
        line2 = u"<i>are belong to</i>"
        line3 = u"<i>Legia Warszawa FC.]</i>"
        line4 = u"The right to consume sausages shall not be abrogated."
        line5 = u"<b>&lt;Chopin must be heard</b>"
        line6 = u"<b>at least</b>"
        line7 = u"<b>per week.&gt;</b>"
        reformatted = self.importer.reformat_text(u""
            + make_tag(line1, top = 100) + u"\n" 
            + make_tag(line2, top = 110) + u"\n"
            + make_tag(line3, top = 120) + u"\n"
            + make_tag(line4, top = 130) + u"\n"
            + make_tag(line5, top = 140) + u"\n"
            + make_tag(line6, top = 150) + u"\n"
            + make_tag(line7, top = 160) + u"\n"            
            + make_fontspec_tag())
        assertEquals(reformatted, "All your base are belong to Legia Warszawa FC. "
                     + "The right to consume sausages shall not be abrogated. "
                     + "Chopin must be heard at least per week.\n")

    def test_reformat_text_remove_hyphenation(self):
        line1 = u"All your base are be-"
        line2 = u"long to Legia Warszawa FC."
        reformatted = self.importer.reformat_text(u""
            + make_tag(line1, top = 100) + u"\n"
            + make_tag(line2, top = 110) + u"\n"
            + make_fontspec_tag())
        assertEquals(reformatted, "All your base are belong to Legia Warszawa FC.\n")
        
        # This checks that for removal of hyphenation the joined text must be on consecutive lines
        # (as above), NOT on the same line (as here).
        reformatted = self.importer.reformat_text(u""
            + make_tag(line1, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line2, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_fontspec_tag())
        assertEquals(reformatted, "All your base are be- long to Legia Warszawa FC.\n")

    def test_reformat_text_keep_linebreak_on_divisions(self):
        line1 = u"DZIAŁ VIII All your base are belong to Legia Warszawa FC."
        line2 = u"DZIAŁ IX The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(u""
            + make_tag(line1, top = 100) + u"\n" 
            + make_tag(line2, top = 110) + u"\n"
            + make_fontspec_tag())
        assertEquals(reformatted, line1 + u"\n" + line2 + u"\n")

    def test_reformat_text_keep_linebreak_on_chapters(self):
        line1 = u"Rozdział 1 All your base are belong to Legia Warszawa FC."
        line2 = u"Rozdział 2 The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(u""
            + make_tag(line1, top = 100) + u"\n" 
            + make_tag(line2, top = 110) + u"\n"
            + make_fontspec_tag())
        assertEquals(reformatted, line1 + u"\n" + line2 + u"\n")

    def test_reformat_text_keep_linebreak_on_statute_level0_units(self):
        line1 = u"Art. 1. All your base are belong to Legia Warszawa FC."
        line2 = u"Art. 2. The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(u""
            + make_tag(line1, top = 100) + u"\n" 
            + make_tag(line2, top = 110) + u"\n"
            + make_fontspec_tag())
        assertEquals(reformatted, line1 + u"\n" + line2 + u"\n")

    def test_reformat_text_keep_linebreak_on_noncode_level1_units(self):
        line1 = u"1. All your base are belong to Legia Warszawa FC."
        line2 = u"2. The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(u""
            + make_tag(line1, top = 100) + u"\n" 
            + make_tag(line2, top = 110) + u"\n"
            + make_fontspec_tag())
        assertEquals(reformatted, line1 + u"\n" + line2 + u"\n")

    def test_reformat_text_keep_linebreak_on_ordinance_level0_or_code_level1_units(self):
        line1 = u"§ 1. All your base are belong to Legia Warszawa FC."
        line2 = u"§ 2. The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(u""
            + make_tag(line1, top = 100) + u"\n" 
            + make_tag(line2, top = 110) + u"\n"
            + make_fontspec_tag())
        assertEquals(reformatted, line1 + u"\n" + line2 + u"\n")

    def test_reformat_text_keep_linebreak_on_points(self):
        line1 = u"1) All your base are belong to Legia Warszawa FC."
        line2 = u"2) The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(u""
            + make_tag(line1, top = 100) + u"\n" 
            + make_tag(line2, top = 110) + u"\n"
            + make_fontspec_tag())
        assertEquals(reformatted, line1 + u"\n" + line2 + u"\n")

    def test_reformat_text_keep_linebreak_on_letters(self):
        line1 = u"a) All your base are belong to Legia Warszawa FC."
        line2 = u"b) The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(u""
            + make_tag(line1, top = 100) + u"\n" 
            + make_tag(line2, top = 110) + u"\n"
            + make_fontspec_tag())
        assertEquals(reformatted, line1 + u"\n" + line2 + u"\n")

    def test_reformat_text_keep_linebreak_complex(self):
        line1 = u"Art. 1ab. Some law."
        line2 = u"2cd. Some law."
        line3 = u"§ 3ef. Some law."
        line4 = u"3gh) Some law."
        line5 = u"ij) Some law."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100) + u"\n" 
            + make_tag(line2, top = 110) + u"\n"
            + make_tag(line3, top = 120) + u"\n"
            + make_tag(line4, top = 130) + u"\n"
            + make_tag(line5, top = 140)
            + make_fontspec_tag())
        assertEquals(reformatted, line1 + u"\n" + line2 + u"\n" + line3 + u"\n" + line4 + u"\n"
                     + line5 + u"\n")        

    def test_reformat_remove_header_footer(self):
        header_text = u"Copyright ISAP"
        text = u"All your base are belong to Legia Warszawa FC."
        footer_text = u"page 3/123"
        reformatted = self.importer.reformat_text(""
            + make_tag(header_text, ImporterPL.HEADER_END_OFFSET - 1)
            + make_tag(text) + make_tag(footer_text, ImporterPL.FOOTER_START_OFFSET + 1)
            + make_fontspec_tag())
        assertEquals(reformatted, u"All your base are belong to Legia Warszawa FC.\n")

    def test_reformat_remove_right_margin(self):
        text = u"All your base are belong to Legia Warszawa FC."
        margin_text = u"Section 123 has been abrogated."
        reformatted = self.importer.reformat_text(""
            + make_tag(text) 
            + make_tag(margin_text, 100, ImporterPL.RIGHT_MARGIN_START_OFFSET + 1)
            + make_fontspec_tag())
        assertEquals(reformatted, u"All your base are belong to Legia Warszawa FC.\n")

    def test_reformat_process_superscripts(self):
        before = u"Some text "
        text1 = u"Art. 123."
        text2 = u"456"
        text3 = u". Bla bla bla "
        after = u"Some other text"
        reformatted = self.importer.reformat_text(""
            + make_tag(before, 90, ImporterPL.INDENT_LEVELS1[0], 18) # Previous line.
            + make_tag(text1, 100, ImporterPL.INDENT_LEVELS1[0], 18)
            + make_tag(text2, 99, ImporterPL.INDENT_LEVELS1[1], 12) # Note lower "top" and "height"
            + make_tag(text3, 100, ImporterPL.INDENT_LEVELS1[2], 18)
            + make_tag(after, 110, ImporterPL.INDENT_LEVELS1[0], 18)
            + make_fontspec_tag()) # Following line.
        assertEquals(reformatted, before.strip() + u"\n"  
                     + text1.strip() + ImporterPL.SUPERSCRIPT_START + text2.strip()
                     + ImporterPL.SUPERSCRIPT_END + text3.strip() + u" " + after.strip() + u"\n")

    def test_reformat_remove_footnotes(self):
        text1 = u"The right "
        text2 = u"to consume "
        text3 = u"sausage "
        text4 = u"shall not "
        text5 = u"be abrogated "
        footnote = u"As promulgated by the Sausage Act of 1 April 1234"
        reformatted = self.importer.reformat_text(""
            + make_tag(text1, top = 100, height = 18, font = 1)
            + make_tag(text2, top = 110, height = 18, font = 1)
            + make_tag(text3, top = 120, height = 18, font = 1)
            + make_tag(text4, top = 130, height = 18, font = 1)
            + make_tag(text5, top = 140, height = 18, font = 1)
            + make_tag(footnote, top = 150, height = 12, font = 3)
            + make_fontspec_tag()) # Different "height" & "font".
        assertEquals(reformatted, text1.strip() + u" " + text2.strip() + u" " + text3.strip() + u" "
                    + text4.strip() + u" " + text5.strip() + u"\n")
        
    def test_reformat_add_newline_if_level0_unit_starts_with_level1_unit_case_1(self):
        line1 = u"Art. 123. 1. All your base are belong to Legia Warszawa FC."
        reformatted = self.importer.reformat_text(make_tag(line1) + make_fontspec_tag())
        assertEquals(reformatted, u"Art. 123.\n1. All your base are belong to Legia Warszawa FC.\n")

    def test_reformat_add_newline_if_level0_unit_starts_with_level1_unit_case_2(self):
        line1 = u"Art. 123. § 1. All your base are belong to Legia Warszawa FC."
        reformatted = self.importer.reformat_text(make_tag(line1) + make_fontspec_tag())
        assertEquals(reformatted, u"Art. 123.\n§ 1. All your base are belong to Legia Warszawa FC.\n")

    def test_reformat_add_newline_if_level0_unit_starts_with_level1_unit_case_3(self):
        line1 = u"§ 123. 1. All your base are belong to Legia Warszawa FC."
        reformatted = self.importer.reformat_text(make_tag(line1) + make_fontspec_tag())
        assertEquals(reformatted, u"§ 123.\n1. All your base are belong to Legia Warszawa FC.\n")

    def test_reformat_add_newline_if_level0_unit_starts_with_level1_unit_case_4(self):
        line1 = u"Art.    123.     1.    All your base are..."
        reformatted = self.importer.reformat_text(make_tag(line1) + make_fontspec_tag())
        assertEquals(reformatted, u"Art.    123.\n1.    All your base are...\n")
        
    def test_reformat_add_newline_if_level0_unit_starts_with_level1_unit_case_5(self):
        line1 = u"Art.    123.     "
        line2 = u"1.    All your base are..."
        reformatted = self.importer.reformat_text(u""
            + make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[0]) 
            + make_tag(line2, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) 
            + make_fontspec_tag())
        assertEquals(reformatted, u"Art.    123.\n1.    All your base are...\n")

    # Start of tests for joining or not joining lines starting with a dash.

    def test_reformat_text_join_statute_level0_continuation_at_indent0_oneline(self):
        line1 =    u"Art. 123. The right to consume sausages"
        line2 = u"– it must never be abrogated."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0])
            + make_fontspec_tag())
        assertEquals(reformatted, 
                     u"Art. 123. The right to consume sausages – it must never be abrogated.\n")
        
    def test_reformat_text_join_statute_level0_continuation_at_indent0_multiline(self):
        line1 =    u"Art. 123. The right to"
        line2 = u"consume sausages"
        line3 = u"– it must never be abrogated."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0])
            + make_fontspec_tag())
        assertEquals(reformatted, 
                     u"Art. 123. The right to consume sausages – it must never be abrogated.\n")

    def test_reformat_text_join_ordinance_level0_continuation_at_indent0_oneline(self):
        line1 =    u"§ 123. The right to consume sausages"
        line2 = u"– it must never be abrogated."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0])
            + make_fontspec_tag())
        assertEquals(reformatted, 
                     u"§ 123. The right to consume sausages – it must never be abrogated.\n")

    def test_reformat_text_join_ordinance_level0_continuation_at_indent0_multiline(self):
        line1 =    u"§ 123. The right to"
        line2 = u"consume sausages"
        line3 = u"– it must never be abrogated."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0])
            + make_fontspec_tag())
        assertEquals(reformatted, 
                     u"§ 123. The right to consume sausages – it must never be abrogated.\n")
        
    def test_reformat_text_join_level0_and_level1_continuation_at_indent0(self):
        line1 =    u"Art. 123. 1. The right to consume sausages"
        line2 = u"– it must never be abrogated."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0])
            + make_fontspec_tag())
        assertEquals(reformatted, 
                     u"Art. 123.\n1. The right to consume sausages – it must never be abrogated.\n")

    def test_reformat_text_join_noncode_point_continuation_at_indent0(self):
        line1 = u"1. The right to consume sausages shall not be abrogated."
        line2 = u"2. The right to consume chicken"
        line3 = u"– it must never be abrogated, too."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0])
            + make_fontspec_tag())
        assertEquals(reformatted,
                     u"1. The right to consume sausages shall not be abrogated.\n" 
                     + u"2. The right to consume chicken – it must never be abrogated, too.\n")

    def test_reformat_text_join_code_point_continuation_at_indent0(self):
        line1 = u"§ 1. The right to consume sausages shall not be abrogated."
        line2 = u"§ 2. The right to consume chicken"
        line3 = u"– it must never be abrogated, too."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0])
            + make_fontspec_tag())
        assert_equal(reformatted, 
                     u"§ 1. The right to consume sausages shall not be abrogated.\n"
                     + u"§ 2. The right to consume chicken – it must never be abrogated, too.\n")

    def test_reformat_text_dont_join_explanatory_section_dash_at_indent0(self):
        line1 =    u"Art. 123. The right to consume sausages:"
        line2 = u"1) at home"
        line3 = u"2) at work"
        line4 = u"– it must never be abrogated."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[0])
            + make_fontspec_tag())
        assertEquals(reformatted,
                     u"Art. 123. The right to consume sausages:\n"
                     + u"1) at home\n"
                     + u"2) at work\n"
                     + u"@@INDENT0@@– it must never be abrogated.\n")

    def test_reformat_text_join_point_continuation_at_indent1_oneline(self):        
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if there is a special place and bla"
        line4 =    u"– and ble as well."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1])
            + make_fontspec_tag())
        assertEquals(reformatted,
                     u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if there is a special place and bla – and ble as well.\n")

    def test_reformat_text_join_point_continuation_at_indent1_multiline(self):        
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if there is a special place"
        line4 =    u"and bla"
        line5 =    u"– and ble as well."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line5, top = 140, left = ImporterPL.INDENT_LEVELS1[1])
            + make_fontspec_tag())
        assertEquals(reformatted,
                     u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if there is a special place and bla – and ble as well.\n")

    def test_reformat_text_dont_join_explanatory_section_dash_at_indent1(self):
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it, or"
        line5 =    u"b) boss is happy with it"
        line6 =    u"– and it's lunch break as defined by workspace regulations."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line5, top = 140, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line6, top = 150, left = ImporterPL.INDENT_LEVELS1[1])
            + make_fontspec_tag())
        assertEquals(reformatted,
                     u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if:\n"
                     + u"a) coworkers are happy with it, or\n"
                     + u"b) boss is happy with it\n"
                     + u"@@INDENT1@@– and it's lunch break as defined by workspace regulations.\n")

    def test_reformat_text_join_letter_continuation_at_indent2(self):        
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it and bla"
        line5 =       u"– and ble as well."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line5, top = 140, left = ImporterPL.INDENT_LEVELS1[2])
            + make_fontspec_tag())
        assertEquals(reformatted,
                     u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if:\n"
                     + u"a) coworkers are happy with it and bla – and ble as well.\n")
        
    def test_reformat_text_dont_join_tirets_at_indent2_oneline(self):
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it, or"
        line5 =    u"b) boss is happy with it, and:"
        line6 =       u"– he is not vegetarian"
        line7 =       u"– he likes you"
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line5, top = 140, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line6, top = 150, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line7, top = 160, left = ImporterPL.INDENT_LEVELS1[2])
            + make_fontspec_tag())
        assertEquals(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if:\n"
                     + u"a) coworkers are happy with it, or\n"
                     + u"b) boss is happy with it, and:\n"
                     + u"@@INDENT2@@– he is not vegetarian\n"
                     + u"@@INDENT2@@– he likes you\n")

    def test_reformat_text_dont_join_tirets_at_indent2_multiline1(self):
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it, or"
        line5 =    u"b) boss is happy with it, he is in"
        line6 =       u"a good mood, and:"
        line7 =       u"– he is not vegetarian"
        line8 =       u"– he likes you"
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line5, top = 140, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line6, top = 150, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line7, top = 160, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line8, top = 170, left = ImporterPL.INDENT_LEVELS1[2])
            + make_fontspec_tag())
        assertEquals(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if:\n"
                     + u"a) coworkers are happy with it, or\n"
                     + u"b) boss is happy with it, he is in a good mood, and:\n"
                     + u"@@INDENT2@@– he is not vegetarian\n"
                     + u"@@INDENT2@@– he likes you\n")

    def test_reformat_text_dont_join_tirets_at_indent2_multiline2(self):
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it, or"
        line5 =    u"b) boss is happy with it, he is in"
        line6 =       u"a good mood, and:    " # Note testing trailing whitespace here.
        line7 =       u"– he is not vegetarian, at least"
        line8 =         u"not today"
        line9 =       u"– he likes you"
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line5, top = 140, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line6, top = 150, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line7, top = 160, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line8, top = 160, left = ImporterPL.INDENT_LEVELS1[3]) + u"\n"
            + make_tag(line9, top = 170, left = ImporterPL.INDENT_LEVELS1[2])
            + make_fontspec_tag())
        assertEquals(reformatted, 
                     u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if:\n"
                     + u"a) coworkers are happy with it, or\n"
                     + u"b) boss is happy with it, he is in a good mood, and:\n"
                     + u"@@INDENT2@@– he is not vegetarian, at least not today\n"
                     + u"@@INDENT2@@– he likes you\n")

    def test_reformat_text_dont_join_double_tirets_at_indent3_oneline(self):
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it, or"
        line5 =    u"b) boss is happy with it, and:"
        line6 =       u"– he likes you"
        line7 =       u"– he is not:"
        line8 =         u"– – vegetarian"
        line9 =         u"– – on a diet"
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line5, top = 140, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line6, top = 150, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line7, top = 160, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line8, top = 170, left = ImporterPL.INDENT_LEVELS1[3]) + u"\n"
            + make_tag(line9, top = 180, left = ImporterPL.INDENT_LEVELS1[3])
            + make_fontspec_tag())
        assertEquals(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                    + u"1) at home\n"
                    + u"2) at work if:\n"
                    + u"a) coworkers are happy with it, or\n"
                    + u"b) boss is happy with it, and:\n"
                    + u"@@INDENT2@@– he likes you\n"
                    + u"@@INDENT2@@– he is not:\n"
                    + u"@@INDENT3@@– – vegetarian\n"
                    + u"@@INDENT3@@– – on a diet\n")

    def test_reformat_text_dont_join_double_tirets_at_indent3_multiline1(self):
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it, or"
        line5 =    u"b) boss is happy with it, and:"
        line6 =       u"– he likes you"
        line7 =       u"– he is"
        line8 =         u"not:"
        line9 =         u"– – vegetarian"
        line10 =        u"– – on a diet"
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line5, top = 140, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line6, top = 150, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line7, top = 160, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line8, top = 170, left = ImporterPL.INDENT_LEVELS1[3]) + u"\n"
            + make_tag(line9, top = 180, left = ImporterPL.INDENT_LEVELS1[3]) + u"\n"
            + make_tag(line10, top = 190, left = ImporterPL.INDENT_LEVELS1[3])
            + make_fontspec_tag())
        assertEquals(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                    + u"1) at home\n"
                    + u"2) at work if:\n"
                    + u"a) coworkers are happy with it, or\n"
                    + u"b) boss is happy with it, and:\n"
                    + u"@@INDENT2@@– he likes you\n"
                    + u"@@INDENT2@@– he is not:\n"
                    + u"@@INDENT3@@– – vegetarian\n"
                    + u"@@INDENT3@@– – on a diet\n")

    def test_reformat_text_dont_join_double_tirets_at_indent3_multiline2(self):
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it, or"
        line5 =    u"b) boss is happy with it, and:"
        line6 =       u"– he likes you"
        line7 =       u"– he is"
        line8 =         u"– not:" # Note the dash here.
        line9 =         u"– – vegetarian"
        line10 =        u"– – on a diet"
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line5, top = 140, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line6, top = 150, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line7, top = 160, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line8, top = 170, left = ImporterPL.INDENT_LEVELS1[3]) + u"\n"
            + make_tag(line9, top = 180, left = ImporterPL.INDENT_LEVELS1[3]) + u"\n"
            + make_tag(line10, top = 190, left = ImporterPL.INDENT_LEVELS1[3])
            + make_fontspec_tag())
        assertEquals(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                    + u"1) at home\n"
                    + u"2) at work if:\n"
                    + u"a) coworkers are happy with it, or\n"
                    + u"b) boss is happy with it, and:\n"
                    + u"@@INDENT2@@– he likes you\n"
                    + u"@@INDENT2@@– he is – not:\n"
                    + u"@@INDENT3@@– – vegetarian\n"
                    + u"@@INDENT3@@– – on a diet\n")

    def test_reformat_text_dont_join_double_tirets_at_indent3_multiline3(self):
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it, or"
        line5 =    u"b) boss is happy with it, and:"
        line6 =       u"– he likes you"
        line7 =       u"– he is not:"
        line8 =         u"– – on"
        line9 =             u"a diet"
        line10 =        u"– – vegetarian"
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line5, top = 140, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line6, top = 150, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line7, top = 160, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line8, top = 170, left = ImporterPL.INDENT_LEVELS1[3]) + u"\n"
            + make_tag(line9, top = 180, left = ImporterPL.INDENT_LEVELS1[4]) + u"\n"
            + make_tag(line10, top = 190, left = ImporterPL.INDENT_LEVELS1[3])
            + make_fontspec_tag())
        assertEquals(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                    + u"1) at home\n"
                    + u"2) at work if:\n"
                    + u"a) coworkers are happy with it, or\n"
                    + u"b) boss is happy with it, and:\n"
                    + u"@@INDENT2@@– he likes you\n"
                    + u"@@INDENT2@@– he is not:\n"
                    + u"@@INDENT3@@– – on a diet\n"
                    + u"@@INDENT3@@– – vegetarian\n")

    def test_reformat_text_dont_join_double_tirets_at_indent3_multiline4(self):
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it, or"
        line5 =    u"b) boss is happy with it, and:"
        line6 =       u"– he likes you"
        line7 =       u"– he is not:"
        line8 =         u"– – on"
        line9 =             u"– a diet" # Note the dash here.
        line10 =        u"– – vegetarian"
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line5, top = 140, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line6, top = 150, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line7, top = 160, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line8, top = 170, left = ImporterPL.INDENT_LEVELS1[3]) + u"\n"
            + make_tag(line9, top = 180, left = ImporterPL.INDENT_LEVELS1[4]) + u"\n"
            + make_tag(line10, top = 190, left = ImporterPL.INDENT_LEVELS1[3])
            + make_fontspec_tag())
        assertEquals(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                    + u"1) at home\n"
                    + u"2) at work if:\n"
                    + u"a) coworkers are happy with it, or\n"
                    + u"b) boss is happy with it, and:\n"
                    + u"@@INDENT2@@– he likes you\n"
                    + u"@@INDENT2@@– he is not:\n"
                    + u"@@INDENT3@@– – on – a diet\n"
                    + u"@@INDENT3@@– – vegetarian\n")

    def test_reformat_text_dont_join_triple_tirets_at_indent4_oneline(self):
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it, or"
        line5 =    u"b) boss is happy with it, and:"
        line6 =       u"– he likes you"
        line7 =       u"– he is not:"
        line8 =         u"– – vegetarian"
        line9 =         u"– – on:"
        line10 =            u"– – – a diet"
        line11 =            u"– – – sausage fast\n"        
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line2, top = 110, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line3, top = 120, left = ImporterPL.INDENT_LEVELS1[0]) + u"\n"
            + make_tag(line4, top = 130, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line5, top = 140, left = ImporterPL.INDENT_LEVELS1[1]) + u"\n"
            + make_tag(line6, top = 150, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line7, top = 160, left = ImporterPL.INDENT_LEVELS1[2]) + u"\n"
            + make_tag(line8, top = 170, left = ImporterPL.INDENT_LEVELS1[3]) + u"\n"
            + make_tag(line9, top = 180, left = ImporterPL.INDENT_LEVELS1[3]) + u"\n"
            + make_tag(line10, top = 190, left = ImporterPL.INDENT_LEVELS1[4]) + u"\n"
            + make_tag(line11, top = 200, left = ImporterPL.INDENT_LEVELS1[4])
            + make_fontspec_tag())
        assertEquals(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                    + u"1) at home\n"
                    + u"2) at work if:\n"
                    + u"a) coworkers are happy with it, or\n"
                    + u"b) boss is happy with it, and:\n"
                    + u"@@INDENT2@@– he likes you\n"
                    + u"@@INDENT2@@– he is not:\n"
                    + u"@@INDENT3@@– – vegetarian\n"
                    + u"@@INDENT3@@– – on:\n"
                    + u"@@INDENT4@@– – – a diet\n"
                    + u"@@INDENT4@@– – – sausage fast\n")

        # TODO: A few more test cases could be added.
