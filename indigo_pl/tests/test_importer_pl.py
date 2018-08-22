# -*- coding: utf-8 -*-

from nose.tools import *  # noqa

from django.test import testcases
from indigo_pl.importer import ImporterPL

def make_tag(text, top = 100, left = 100, height = 18, indent = 0):
    return (u"<text top='" + utfify(top) 
            + u"' left='" + utfify(left) 
            + u"' height='" + utfify(height) 
            + u"' indent='" + utfify(indent) + u"'>" + text + u"</text>")

def utfify(num):
    return str(num).encode("utf-8").decode("utf-8")

def make_tags_for_indent_level(initial_top, left):
    """Creates a number of <text> tags to add to test text, in order to have a certain indentation
    level appear more than ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD times in the text. Only then
    the parser will recognize it as a valid indentation level.
    """
    result = u""
    for _ in range(ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD):
        result = result + u"\n" + make_tag(u"X", initial_top, left)
        initial_top = initial_top + 10
    return result

class ImporterPLTestCase(testcases.TestCase):

    def setUp(self):
        self.importer = ImporterPL()

    def test_reformat_text_simple(self):
        line1 = u"All your base are belong"
        line2 = u"to Legia Warszawa FC."
        reformatted = self.importer.reformat_text(make_tag(line1) + u"\n" + make_tag(line2))
        assert_equal(reformatted, "All your base are belong to Legia Warszawa FC.")

    def test_reformat_text_remove_hyphenation(self):
        line1 = u"All your base are be-"
        line2 = u"long to Legia Warszawa FC."
        reformatted = self.importer.reformat_text(make_tag(line1) + u"\n" + make_tag(line2))
        assert_equal(reformatted, "All your base are belong to Legia Warszawa FC.")

    def test_reformat_text_keep_linebreak_on_divisions(self):
        line1 = u"DZIAŁ VIII All your base are belong to Legia Warszawa FC."
        line2 = u"DZIAŁ IX The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(make_tag(line1) + u"\n" + make_tag(line2))
        assert_equal(reformatted, line1 + u"\n" + line2)

    def test_reformat_text_keep_linebreak_on_chapters(self):
        line1 = u"Rozdział 1 All your base are belong to Legia Warszawa FC."
        line2 = u"Rozdział 2 The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(make_tag(line1) + u"\n" + make_tag(line2))
        assert_equal(reformatted, line1 + u"\n" + line2)

    def test_reformat_text_keep_linebreak_on_statute_level0_units(self):
        line1 = u"Art. 1. All your base are belong to Legia Warszawa FC."
        line2 = u"Art. 2. The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(make_tag(line1) + u"\n" + make_tag(line2))
        assert_equal(reformatted, line1 + u"\n" + line2)

    def test_reformat_text_keep_linebreak_on_noncode_level1_units(self):
        line1 = u"1. All your base are belong to Legia Warszawa FC."
        line2 = u"2. The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(make_tag(line1) + u"\n" + make_tag(line2))
        assert_equal(reformatted, line1 + u"\n" + line2)

    def test_reformat_text_keep_linebreak_on_ordinance_level0_or_code_level1_units(self):
        line1 = u"§ 1. All your base are belong to Legia Warszawa FC."
        line2 = u"§ 2. The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(make_tag(line1) + u"\n" + make_tag(line2))
        assert_equal(reformatted, line1 + u"\n" + line2)

    def test_reformat_text_keep_linebreak_on_points(self):
        line1 = u"1) All your base are belong to Legia Warszawa FC."
        line2 = u"2) The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(make_tag(line1) + u"\n" + make_tag(line2))
        assert_equal(reformatted, line1 + u"\n" + line2)

    def test_reformat_text_keep_linebreak_on_letters(self):
        line1 = u"a) All your base are belong to Legia Warszawa FC."
        line2 = u"b) The right to consume sausages shall not be abrogated."
        reformatted = self.importer.reformat_text(make_tag(line1) + u"\n" + make_tag(line2))
        assert_equal(reformatted, line1 + u"\n" + line2)

    def test_reformat_text_keep_linebreak_complex(self):
        line1 = u"Art. 1ab. Some law."
        line2 = u"2cd. Some law."
        line3 = u"§ 3ef. Some law."
        line4 = u"3gh) Some law."
        line5 = u"ij) Some law."
        reformatted = self.importer.reformat_text(
            make_tag(line1) + u"\n" 
            + make_tag(line2) + u"\n"
            + make_tag(line3) + u"\n"
            + make_tag(line4) + u"\n"
            + make_tag(line5))
        assert_equal(reformatted, line1 + u"\n" + line2 + u"\n" + line3 + u"\n" + line4 + u"\n"
                     + line5)        

    def test_reformat_remove_header_footer(self):
        header_text = u"Copyright ISAP"
        text = u"All your base are belong to Legia Warszawa FC."
        footer_text = u"page 3/123"
        reformatted = self.importer.reformat_text(""
            + make_tag(header_text, ImporterPL.HEADER_END_OFFSET - 1)
            + make_tag(text) + make_tag(footer_text, ImporterPL.FOOTER_START_OFFSET + 1))
        assert_equal(reformatted, text)

    def test_reformat_process_superscripts(self):
        before = u"Some text "
        text1 = u"Art. 123."
        text2 = u"456"
        text3 = u". Bla bla bla "
        after = u"Some other text"
        reformatted = self.importer.reformat_text(""
            + make_tag(before, 90, 100, 18) # Previous line.
            + make_tag(text1, 100, 100, 18)
            + make_tag(text2, 99, 100, 12) # Note lower "top" and "height" attributes
            + make_tag(text3, 100, 100, 18)
            + make_tag(after, 110, 100, 18)) # Following line.
        assert_equal(reformatted, before + text1 + ImporterPL.SUPERSCRIPT_START + text2 
                     + ImporterPL.SUPERSCRIPT_END + text3 + after)

    def test_reformat_remove_footnotes(self):
        text1 = u"The right "
        text2 = u"to consume "
        text3 = u"sausage "
        text4 = u"shall not "
        text5 = u"be abrogated "
        footnote = u"As promulgated by the Sausage Act of 1 April 1234"
        reformatted = self.importer.reformat_text(""
            + make_tag(text1, 100, 100, 18)
            + make_tag(text2, 110, 100, 18)
            + make_tag(text3, 120, 100, 18)
            + make_tag(text4, 130, 100, 18)
            + make_tag(text5, 140, 100, 18)
            + make_tag(footnote, 150, 100, 12)) # Note lower "height" attribute.
        assert_equal(reformatted, text1 + text2 + text3 + text4 + text5)
        
    def test_reformat_add_newline_if_level0_unit_starts_with_level1_unit_case_1(self):
        line1 = u"Art. 123. 1. All your base are belong to Legia Warszawa FC."
        reformatted = self.importer.reformat_text(make_tag(line1))
        assert_equal(reformatted, u"Art. 123.\n1. All your base are belong to Legia Warszawa FC.")

    def test_reformat_add_newline_if_level0_unit_starts_with_level1_unit_case_2(self):
        line1 = u"Art. 123. § 1. All your base are belong to Legia Warszawa FC."
        reformatted = self.importer.reformat_text(make_tag(line1))
        assert_equal(reformatted, u"Art. 123.\n§ 1. All your base are belong to Legia Warszawa FC.")

    def test_reformat_add_newline_if_level0_unit_starts_with_level1_unit_case_3(self):
        line1 = u"§ 123. 1. All your base are belong to Legia Warszawa FC."
        reformatted = self.importer.reformat_text(make_tag(line1))
        assert_equal(reformatted, u"§ 123.\n1. All your base are belong to Legia Warszawa FC.")

    def test_reformat_add_newline_if_level0_unit_starts_with_level1_unit_case_4(self):
        line1 = u"Art.    123.     1.    All your base are..."
        reformatted = self.importer.reformat_text(make_tag(line1))
        assert_equal(reformatted, u"Art.    123.\n1.    All your base are...")

    # Start of tests for joining or not joining lines starting with a dash.

    def test_reformat_text_join_statute_level0_continuation_at_indent0_oneline(self):
        line1 =    u"Art. 123. The right to consume sausages"
        line2 = u"– it must never be abrogated."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210) 
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted, 
                     u"Art. 123. The right to consume sausages – it must never be abrogated."
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 2)
        
    def test_reformat_text_join_statute_level0_continuation_at_indent0_multiline(self):
        line1 =    u"Art. 123. The right to"
        line2 = u"consume sausages"
        line3 = u"– it must never be abrogated."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210) 
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted, 
                     u"Art. 123. The right to consume sausages – it must never be abrogated."
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 2)

    def test_reformat_text_join_ordinance_level0_continuation_at_indent0_oneline(self):
        line1 =    u"§ 123. The right to consume sausages"
        line2 = u"– it must never be abrogated."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted, 
                     u"§ 123. The right to consume sausages – it must never be abrogated."
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 2)

    def test_reformat_text_join_ordinance_level0_continuation_at_indent0_multiline(self):
        line1 =    u"§ 123. The right to"
        line2 = u"consume sausages"
        line3 = u"– it must never be abrogated."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted, 
                     u"§ 123. The right to consume sausages – it must never be abrogated."
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 2)
        
    def test_reformat_text_join_level0_and_level1_continuation_at_indent0(self):
        line1 =    u"Art. 123. 1. The right to consume sausages"
        line2 = u"– it must never be abrogated."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210) 
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted, 
                     u"Art. 123.\n1. The right to consume sausages – it must never be abrogated."
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 2)

    def test_reformat_text_join_noncode_point_continuation_at_indent0(self):
        line1 = u"1. The right to consume sausages shall not be abrogated."
        line2 = u"2. The right to consume chicken"
        line3 = u"– it must never be abrogated, too."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                     u"1. The right to consume sausages shall not be abrogated.\n" 
                     + u"2. The right to consume chicken – it must never be abrogated, too."
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 2)

    def test_reformat_text_join_code_point_continuation_at_indent0(self):
        line1 = u"§ 1. The right to consume sausages shall not be abrogated."
        line2 = u"§ 2. The right to consume chicken"
        line3 = u"– it must never be abrogated, too."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted, 
                     u"§ 1. The right to consume sausages shall not be abrogated.\n"
                     + u"§ 2. The right to consume chicken – it must never be abrogated, too."
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 2)

    def test_reformat_text_dont_join_explanatory_section_dash_at_indent0(self):
        line1 =    u"Art. 123. The right to consume sausages:"
        line2 = u"1) at home"
        line3 = u"2) at work"
        line4 = u"– it must never be abrogated."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 200)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210) 
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                     u"Art. 123. The right to consume sausages:\n"
                     + u"1) at home\n"
                     + u"2) at work\n"
                     + u"@@INDENT0@@– it must never be abrogated."                     
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 2)

    def test_reformat_text_join_point_continuation_at_indent1_oneline(self):        
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if there is a special place and bla"
        line4 =    u"– and ble as well."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210) 
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                     u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if there is a special place and bla – and ble as well."
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 2)

    def test_reformat_text_join_point_continuation_at_indent1_multiline(self):        
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if there is a special place"
        line4 =    u"and bla"
        line5 =    u"– and ble as well."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210) + u"\n"
            + make_tag(line5, top = 140, left = 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210) 
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                     u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if there is a special place and bla – and ble as well."
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 2)

    def test_reformat_text_dont_join_explanatory_section_dash_at_indent1(self):
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it, or"
        line5 =    u"b) boss is happy with it"
        line6 =    u"– and it's lunch break as defined by workspace regulations."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210) + u"\n"
            + make_tag(line5, top = 140, left = 210) + u"\n"
            + make_tag(line6, top = 150, left = 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210) 
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                     u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if:\n"
                     + u"a) coworkers are happy with it, or\n"
                     + u"b) boss is happy with it\n"
                     + u"@@INDENT1@@– and it's lunch break as defined by workspace regulations."
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 2)

    def test_reformat_text_join_letter_continuation_at_indent2(self):        
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it and bla"
        line5 =       u"– and ble as well."
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210) + u"\n"
            + make_tag(line5, top = 140, left = 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 300, 220) 
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210) 
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                     u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if:\n"
                     + u"a) coworkers are happy with it and bla – and ble as well."
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 3)
        
    def test_reformat_text_dont_join_tirets_at_indent2_oneline(self):
        line1 =    u"Art. 123. The right to consume sausages shall not be abrogated:"
        line2 = u"1) at home"
        line3 = u"2) at work if:"
        line4 =    u"a) coworkers are happy with it, or"
        line5 =    u"b) boss is happy with it, and:"
        line6 =       u"– he is not vegetarian"
        line7 =       u"– he likes you"
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210) + u"\n"
            + make_tag(line5, top = 140, left = 210) + u"\n"
            + make_tag(line6, top = 150, left = 220) + u"\n"
            + make_tag(line7, top = 160, left = 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 300, 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if:\n"
                     + u"a) coworkers are happy with it, or\n"
                     + u"b) boss is happy with it, and:\n"
                     + u"@@INDENT2@@– he is not vegetarian\n"
                     + u"@@INDENT2@@– he likes you"
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 3)

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
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210) + u"\n"
            + make_tag(line5, top = 140, left = 210) + u"\n"
            + make_tag(line6, top = 150, left = 220) + u"\n"
            + make_tag(line7, top = 160, left = 220) + u"\n"
            + make_tag(line8, top = 170, left = 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 300, 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if:\n"
                     + u"a) coworkers are happy with it, or\n"
                     + u"b) boss is happy with it, he is in a good mood, and:\n"
                     + u"@@INDENT2@@– he is not vegetarian\n"
                     + u"@@INDENT2@@– he likes you"
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 3)

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
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210) + u"\n"
            + make_tag(line5, top = 140, left = 210) + u"\n"
            + make_tag(line6, top = 150, left = 220) + u"\n"
            + make_tag(line7, top = 160, left = 220) + u"\n"
            + make_tag(line8, top = 160, left = 230) + u"\n"
            + make_tag(line9, top = 170, left = 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 400, 230)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 300, 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted, 
                     u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                     + u"1) at home\n"
                     + u"2) at work if:\n"
                     + u"a) coworkers are happy with it, or\n"
                     + u"b) boss is happy with it, he is in a good mood, and:    \n"
                     + u"@@INDENT2@@– he is not vegetarian, at least not today\n"
                     + u"@@INDENT2@@– he likes you"
                     + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 4)

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
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210) + u"\n"
            + make_tag(line5, top = 140, left = 210) + u"\n"
            + make_tag(line6, top = 150, left = 220) + u"\n"
            + make_tag(line7, top = 160, left = 220) + u"\n"
            + make_tag(line8, top = 170, left = 230) + u"\n"
            + make_tag(line9, top = 180, left = 230)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 400, 230)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 300, 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                    + u"1) at home\n"
                    + u"2) at work if:\n"
                    + u"a) coworkers are happy with it, or\n"
                    + u"b) boss is happy with it, and:\n"
                    + u"@@INDENT2@@– he likes you\n"
                    + u"@@INDENT2@@– he is not:\n"
                    + u"@@INDENT3@@– – vegetarian\n"
                    + u"@@INDENT3@@– – on a diet"
                    + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 4)

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
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210) + u"\n"
            + make_tag(line5, top = 140, left = 210) + u"\n"
            + make_tag(line6, top = 150, left = 220) + u"\n"
            + make_tag(line7, top = 160, left = 220) + u"\n"
            + make_tag(line8, top = 170, left = 230) + u"\n"
            + make_tag(line9, top = 180, left = 230) + u"\n"
            + make_tag(line10, top = 190, left = 230)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 400, 230)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 300, 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                    + u"1) at home\n"
                    + u"2) at work if:\n"
                    + u"a) coworkers are happy with it, or\n"
                    + u"b) boss is happy with it, and:\n"
                    + u"@@INDENT2@@– he likes you\n"
                    + u"@@INDENT2@@– he is not:\n"
                    + u"@@INDENT3@@– – vegetarian\n"
                    + u"@@INDENT3@@– – on a diet"                     
                    + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 4)

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
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210) + u"\n"
            + make_tag(line5, top = 140, left = 210) + u"\n"
            + make_tag(line6, top = 150, left = 220) + u"\n"
            + make_tag(line7, top = 160, left = 220) + u"\n"
            + make_tag(line8, top = 170, left = 230) + u"\n"
            + make_tag(line9, top = 180, left = 230) + u"\n"
            + make_tag(line10, top = 190, left = 230)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 400, 230)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 300, 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                    + u"1) at home\n"
                    + u"2) at work if:\n"
                    + u"a) coworkers are happy with it, or\n"
                    + u"b) boss is happy with it, and:\n"
                    + u"@@INDENT2@@– he likes you\n"
                    + u"@@INDENT2@@– he is – not:\n"
                    + u"@@INDENT3@@– – vegetarian\n"
                    + u"@@INDENT3@@– – on a diet"                     
                    + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 4)

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
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210) + u"\n"
            + make_tag(line5, top = 140, left = 210) + u"\n"
            + make_tag(line6, top = 150, left = 220) + u"\n"
            + make_tag(line7, top = 160, left = 220) + u"\n"
            + make_tag(line8, top = 170, left = 230) + u"\n"
            + make_tag(line9, top = 180, left = 240) + u"\n"
            + make_tag(line10, top = 190, left = 230)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 500, 240)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 400, 230)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 300, 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                    + u"1) at home\n"
                    + u"2) at work if:\n"
                    + u"a) coworkers are happy with it, or\n"
                    + u"b) boss is happy with it, and:\n"
                    + u"@@INDENT2@@– he likes you\n"
                    + u"@@INDENT2@@– he is not:\n"
                    + u"@@INDENT3@@– – on a diet\n"
                    + u"@@INDENT3@@– – vegetarian"                    
                    + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 5)

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
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210) + u"\n"
            + make_tag(line5, top = 140, left = 210) + u"\n"
            + make_tag(line6, top = 150, left = 220) + u"\n"
            + make_tag(line7, top = 160, left = 220) + u"\n"
            + make_tag(line8, top = 170, left = 230) + u"\n"
            + make_tag(line9, top = 180, left = 240) + u"\n"
            + make_tag(line10, top = 190, left = 230)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 500, 240)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 400, 230)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 300, 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
                    u"Art. 123. The right to consume sausages shall not be abrogated:\n"
                    + u"1) at home\n"
                    + u"2) at work if:\n"
                    + u"a) coworkers are happy with it, or\n"
                    + u"b) boss is happy with it, and:\n"
                    + u"@@INDENT2@@– he likes you\n"
                    + u"@@INDENT2@@– he is not:\n"
                    + u"@@INDENT3@@– – on – a diet\n"
                    + u"@@INDENT3@@– – vegetarian"                    
                    + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 5)

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
        line11 =            u"– – – sausage fast"        
        reformatted = self.importer.reformat_text(
            make_tag(line1, top = 100, left = 210) + u"\n"
            + make_tag(line2, top = 110, left = 200) + u"\n"
            + make_tag(line3, top = 120, left = 200) + u"\n"
            + make_tag(line4, top = 130, left = 210) + u"\n"
            + make_tag(line5, top = 140, left = 210) + u"\n"
            + make_tag(line6, top = 150, left = 220) + u"\n"
            + make_tag(line7, top = 160, left = 220) + u"\n"
            + make_tag(line8, top = 170, left = 230) + u"\n"
            + make_tag(line9, top = 180, left = 230) + u"\n"
            + make_tag(line10, top = 190, left = 240) + u"\n"
            + make_tag(line11, top = 200, left = 240) + u"\n"
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 500, 240)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 400, 230)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 300, 220)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 200, 210)
            + make_tags_for_indent_level(ImporterPL.FOOTER_START_OFFSET - 100, 200))
        assert_equal(reformatted,
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
                    + u"@@INDENT4@@– – – sausage fast"
                    + u" X" * ImporterPL.INDENT_LEVEL_FREQUENCY_THRESHOLD * 5)

        # TODO: A few more test cases could be added.
