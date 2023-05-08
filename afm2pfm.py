# MIT License
#
# Copyright (c) 2023 GUST (Piotr Strzelczyk)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
AFM2PFM converter: simple tool for creating PFM files needed to install Type1 fonts in Windows system.
Information needed to create a PFM file is extracted from AFM (text) file and converted into binary PFM.
"""

import argparse
import math
import re
import struct
import typing

VERSION = "0.30"
PFM_HEADER = [
    ('H', 'Version'),
    ('I', 'Size'),
    ('60s', 'Copyright'),
    ('H', 'Type'),
    ('H', 'Points'),
    ('H', 'VertRes'),
    ('H', 'HorizRes'),
    ('H', 'Ascent'),
    ('H', 'InternalLeading'),
    ('H', 'ExternalLeading'),
    ('B', 'Italic'),
    ('B', 'Underline'),
    ('B', 'Stikeout'),
    ('H', 'Weight'),
    ('B', 'CharSet'),
    ('H', 'PixWidth'),
    ('H', 'PixHeight'),
    ('B', 'PitchAndFamily'),
    ('H', 'AvgWidth'),
    ('H', 'MaxWidth'),
    ('B', 'FirstChar'),
    ('B', 'LastChar'),
    ('B', 'DefaultChar'),
    ('B', 'BreakChar'),
    ('H', 'WidthBytes'),
    ('I', 'Device'),
    ('I', 'Face'),
    ('I', 'BitsPointer'),
    ('I', 'BitsOffset'),
    ('H', 'SizeFields'),
    ('I', 'ExtMetricOffset'),
    ('I', 'ExtentTable'),
    ('I', 'OriginTable'),
    ('I', 'PairKernTable'),
    ('I', 'TrackKernTable'),
    ('I', 'DriverInfo'),
    ('I', 'Reserved')
]
PFM_EXTMETRIC = [
    ('h', 'Size_ext'),
    ('h', 'PointSize'),
    ('h', 'Orientation'),
    ('h', 'MasterHeight'),
    ('h', 'MinScale'),
    ('h', 'MaxScale'),
    ('h', 'MasterUnits'),
    ('h', 'CapHeight'),
    ('h', 'XHeight'),
    ('h', 'LowerCaseAscent'),
    ('h', 'LowerCaseDescent'),
    ('h', 'Slant'),
    ('h', 'SuperScript'),
    ('h', 'SubScript'),
    ('h', 'SuperScriptSize'),
    ('h', 'SubScriptSize'),
    ('h', 'UnderlineOffset'),
    ('h', 'UnderlineWidth'),
    ('h', 'DoubleUpperUnderlineOffset'),
    ('h', 'DoubleLowerUnderlineOffset'),
    ('h', 'DoubleUpperUnderlineWidth'),
    ('h', 'DoubleLowerUnderlineWidth'),
    ('h', 'StrikeOutOffset'),
    ('h', 'StrikeOutWidth'),
    ('H', 'KernPairs'),
    ('H', 'KernTracks')
]
PFM_STRINGS = [  # strings with variable length
    ('Device', 'DeviceName'),
    ('Face', 'WindowsName'),
    ('DriverInfo', 'PostscriptName')
]
PAT_LENGTHS = {'B': 1, 'h': 2, 'H': 2, 'I': 4, '60s': 60}

PFM_TABLES_ORDER = 1
PFM_EXTRA_VALUES = {
    'Info': 'JNSteam'
}

STRING_ENCODING = "latin-1"
WEIGTHS = {  # magic numbers
    'Light': 300,
    'Regular': 400,
    'Normal': 400,
    'Book': 400,
    'Medium': 500,
    'Demi': 500,
    'Bold': 700,
    'Black': 1000
}
AFM_HEADERS_DEFAULTS = {
    'FontName': "FontAnna",
    'Weight': WEIGTHS['Regular'],
    'ItalicAngle': 0,
    'IsFixedPitch': 'false',
    'CapHeight': 750,
    'XHeight': 400,
    'Descender': -250,
    'Ascender': 750,
    'UnderlinePosition': -200,
    'UnderlineThickness': 40,
    'EncodingScheme': "FontSpecific",  # not used
    'Version': "0.000",  # not used
    'FullName': "FontAnna",  # not used
    'FamilyName': "FontAnna"  # not used
}


class PfmWriter:
    """
    Simple PFM file writer, converts fonts information given in data structures
    and writes a binary PFM file (needed to install Type 1 font in Windows).
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.pfm_header = []
        self.pfm_names = []
        self.pfm_offsets = {}
        self.pfm_template = {}
        self.pfm_values = {}
        self.calculated_size = 0

        self.pfm_head_length = 0
        self.pfm_head_template = '<'
        for pat, name in PFM_HEADER:
            self.pfm_names.append(name)
            self.pfm_template[name] = pat
            self.pfm_head_template += pat
            self.pfm_offsets[name] = self.pfm_head_length
            self.pfm_head_length += PAT_LENGTHS[pat]

        self.pfm_ext_start = len(self.pfm_names)
        self.pfm_ext_offset = self.pfm_head_length + 1
        self.pfm_ext_length = 0
        self.pfm_ext_template = '<'
        for pat, name in PFM_EXTMETRIC:
            self.pfm_names.append(name)
            self.pfm_template[name] = pat
            self.pfm_ext_template += pat
            self.pfm_offsets[name] = self.pfm_ext_offset + self.pfm_ext_length
            self.pfm_ext_length += PAT_LENGTHS[pat]

        self.pfm_strings_start = len(self.pfm_names)
        for _, name in PFM_STRINGS:
            self.pfm_names.append(name)

        self.pfm_extra_values_start = len(self.pfm_names)

        self.pfm_widths_offset = 0
        self.pfm_widths_length = 0
        self.pfm_widths_template = '<'
        self.pfm_widths = []

        self.pfm_kerns_num = 0
        self.pfm_kerns_offset = 0
        self.pfm_kerns_length = 0
        self.pfm_kerns_template = '<'
        self.pfm_kerns = []

    def set_default_values(self):
        self.pfm_values['Version'] = 256
        self.pfm_values['Type'] = 129
        self.pfm_values['Points'] = 10
        self.pfm_values['VertRes'] = 300
        self.pfm_values['HorizRes'] = 300
        self.pfm_values['ExternalLeading'] = 0
        self.pfm_values['Underline'] = 0
        self.pfm_values['Stikeout'] = 0
        self.pfm_values['WidthBytes'] = 0
        self.pfm_values['BitsPointer'] = 0
        self.pfm_values['BitsOffset'] = 0
        self.pfm_values['SizeFields'] = 30
        self.pfm_values['OriginTable'] = 0
        self.pfm_values['TrackKernTable'] = 0
        self.pfm_values['Reserved'] = 0
        self.pfm_values['Size_ext'] = self.pfm_ext_length
        self.pfm_values['PointSize'] = 200
        self.pfm_values['Orientation'] = 0
        self.pfm_values['MasterHeight'] = 1000
        self.pfm_values['MinScale'] = 4
        self.pfm_values['MaxScale'] = 900
        self.pfm_values['MasterUnits'] = 1000
        self.pfm_values['KernTracks'] = 0
        self.pfm_values['DeviceName'] = 'PostScript'

    def prepare_data(self, afm_values: dict, afm_widths: list, afm_kerns: list, extra_args: dict, no_kern_limit):
        """ Method that gets external data and sets all values needed for PFM file """

        def rounds(x):
            return round(float(x))

        def ceiling(x):
            return int(math.ceil(float(x)))

        def floor(x):
            return int(math.floor(float(x)))

        for key, value in AFM_HEADERS_DEFAULTS.items():
            if key not in afm_values:
                print(f"Missing AFM value: {key}, assuming: {value}.")
                afm_values[key] = value

        self.set_default_values()

        self.pfm_values['PostscriptName'] = afm_values['FontName']
        self.pfm_values['Copyright'] = (afm_values['Notice'] + " " * 60)[:60].encode(STRING_ENCODING)
        self.pfm_values['Ascent'] = ceiling(afm_values['ury'])
        self.pfm_values['InternalLeading'] = max(0, ceiling(afm_values['ury']) - floor(afm_values['lly']) - 1000)
        self.pfm_values['Italic'] = 1 if float(afm_values['ItalicAngle']) != 0 else 0
        name_suffix = re.search(
            r"[^A-Za-z](Light|Regular| Normal|Medium|Book|Demi|Bold|Black)",
            afm_values['FontName'])
        self.pfm_values['Weight'] = (
            WEIGTHS[name_suffix[1]] if name_suffix and name_suffix[1] in WEIGTHS
            else WEIGTHS['Regular'])
        self.pfm_values['CharSet'] = 255
        self.pfm_values['PixWidth'] = max(0, ceiling(afm_values['urx']) - floor(afm_values['llx']))
        self.pfm_values['PixHeight'] = 1000 + self.pfm_values['InternalLeading']
        self.pfm_values['PitchAndFamily'] = 16 * 1 + (0 if afm_values['IsFixedPitch'].lower() == 'true' else 1)
        self.pfm_values['AvgWidth'] = rounds(afm_values["AVG_WIDTH"]) if afm_values["AVG_WIDTH"] else 500
        self.pfm_values['MaxWidth'] = rounds(afm_values["MAX_WIDTH"])
        self.pfm_values['FirstChar'] = 0
        self.pfm_values['LastChar'] = 255
        self.pfm_values['DefaultChar'] = (
            afm_values["DEFAULT_CHAR"] if afm_values["DEFAULT_CHAR"] else ord('?')
        ) - self.pfm_values['FirstChar']
        self.pfm_values['BreakChar'] = ord(' ') - self.pfm_values['FirstChar']
        self.pfm_values['CapHeight'] = rounds(afm_values['CapHeight'])
        self.pfm_values['XHeight'] = rounds(afm_values['XHeight'])
        self.pfm_values['LowerCaseAscent'] = rounds(afm_values['Ascender'])
        self.pfm_values['LowerCaseDescent'] = rounds(-float(afm_values['Descender']))
        self.pfm_values['Slant'] = rounds(10 * float(afm_values['ItalicAngle']))
        self.pfm_values['SuperScript'] = - rounds(0.8 * float(self.pfm_values['XHeight']))
        self.pfm_values['SubScript'] = rounds(0.3 * float(self.pfm_values['XHeight']))
        self.pfm_values['SuperScriptSize'] = 800
        self.pfm_values['SubScriptSize'] = 800
        self.pfm_values['UnderlineOffset'] = rounds(-float(afm_values['UnderlinePosition']))
        self.pfm_values['UnderlineWidth'] = rounds(afm_values['UnderlineThickness'])
        self.pfm_values['DoubleUpperUnderlineOffset'] = self.pfm_values['UnderlineOffset']
        self.pfm_values['DoubleLowerUnderlineOffset'] = rounds(
            self.pfm_values['DoubleUpperUnderlineOffset']
            + 3 * self.pfm_values['UnderlineWidth'])
        self.pfm_values['DoubleUpperUnderlineWidth'] = self.pfm_values['UnderlineWidth']
        self.pfm_values['DoubleLowerUnderlineWidth'] = self.pfm_values['UnderlineWidth']
        self.pfm_values['StrikeOutOffset'] = rounds(0.6 * float(self.pfm_values['XHeight']))
        self.pfm_values['StrikeOutWidth'] = self.pfm_values['UnderlineWidth']

        if 'PFMname' in afm_values:
            self.pfm_values['WindowsName'] = afm_values['PFMname']
        else:
            name_suffixes = re.compile(
                r"([Oo]bli(que)? |[Ii]t(alic)? |[Kk]ursywa |[Ss]lant(ed)? |Lt |[Ll]ight |[Rr]eg(ular)? |[Nn]or(mal)?"
                r"|Bk |[Bb]ook |Dm |[Dd]emi |Md |[Mm]edium |Bd |[Bb]old |Blk |[Bb]lack |[\ _\-:])+$", re.VERBOSE
            )
            self.pfm_values['WindowsName'] = name_suffixes.sub("", afm_values['FontName'])

        if 'PFMbold' in afm_values:
            self.pfm_values['Weight'] = rounds(afm_values['PFMbold']) if float(afm_values['PFMbold']) > 10 else (
                WEIGTHS['Regular'] if float(afm_values['PFMbold']) == 0 else WEIGTHS['Bold']
            )

        if 'PFMitalic' in afm_values:
            self.pfm_values['Italic'] = 0 if float(afm_values['PFMitalic']) == 0 else 1

        if 'PFMcharset' in afm_values:
            self.pfm_values['CharSet'] = int(afm_values['PFMcharset'])

        self.prepare_widths(afm_widths)
        self.prepare_kerns(afm_kerns, no_kern_limit)

        for key, value in PFM_EXTRA_VALUES.items():
            self.put_extra_values(key, value)

        for key, value in extra_args.items():
            if key in self.pfm_values:
                self.pfm_values[key] = value
            else:
                raise ValueError(f"Unknown key in command line parameter {key}")
        if self.verbose:
            for key, value in self.pfm_values.items():
                print(f"{key:20s} {value}")

    def prepare_widths(self, afm_widths: list):
        pfm_widths_num = self.pfm_values['LastChar'] - self.pfm_values['FirstChar'] + 1
        self.pfm_widths_length = pfm_widths_num * 2
        self.pfm_widths_template += 'H' * pfm_widths_num
        self.pfm_widths = []

        for i in range(self.pfm_values['FirstChar'], self.pfm_values['LastChar'] + 1):
            if afm_widths[i] is not None:
                self.pfm_widths.append(round(afm_widths[i]))
            else:
                self.pfm_widths.append(self.pfm_values['AvgWidth'])

    def prepare_kerns(self, afm_kerns: list, no_kern_limit):
        if afm_kerns:
            if len(afm_kerns) > 511:
                if no_kern_limit:
                    print(f"A2P: The number of kerns is {len(afm_kerns)} (more than allowed 512).")
                else:
                    afm_kerns.sort(key=lambda x: abs(x[2]), reverse=True)
                    deleted = afm_kerns[512:]
                    afm_kerns = afm_kerns[:512]
                    print(
                        f"A2P: The number of kerns reduced by {len(deleted)} (values <={abs(deleted[0][2])} deleted)."
                    )
            afm_kerns.sort(key=lambda x: (x[1], x[0]))
            self.pfm_kerns_num = len(afm_kerns)
            self.pfm_kerns_length = self.pfm_kerns_num * 4 + 2  # +2 for undocumented length of kern table
            self.pfm_kerns_template += "BBh" * self.pfm_kerns_num
            self.pfm_kerns = []

            for i in afm_kerns:
                self.pfm_kerns.extend([i[0], i[1], round(i[2])])  # was: int() !

        self.pfm_values['KernPairs'] = self.pfm_kerns_num

    def put_extra_values(self, name, value):
        self.pfm_names.append(name)
        self.pfm_values[name] = value
        self.pfm_template[name] = f"{1 + len(value)}s"

    def calculate_offsets(self):
        """ Recalculates lengths of all PFM data blocks and sets pointers to structures. """
        offset = 0
        offset += self.pfm_head_length

        if PFM_TABLES_ORDER:  # order according to Y&Y
            self.pfm_values['ExtMetricOffset'] = offset
            self.pfm_ext_offset = offset
            offset += self.pfm_ext_length
            self.pfm_values['Device'] = offset
            self.pfm_offsets['DeviceName'] = offset
            offset += len(self.pfm_values['DeviceName']) + 1
            self.pfm_values['Face'] = offset
            self.pfm_offsets['WindowsName'] = offset
            offset += len(self.pfm_values['WindowsName']) + 1
            self.pfm_values['DriverInfo'] = offset
            self.pfm_offsets['PostscriptName'] = offset
            offset += len(self.pfm_values['PostscriptName']) + 1

            for i in range(self.pfm_extra_values_start, len(self.pfm_names)):
                self.pfm_offsets[self.pfm_names[i]] = offset
                offset += len(self.pfm_values[self.pfm_names[i]]) + 1

            self.pfm_values['ExtentTable'] = offset
            self.pfm_widths_offset = offset
            offset += self.pfm_widths_length

            if self.pfm_kerns_num > 0:
                self.pfm_values['PairKernTable'] = offset
                self.pfm_kerns_offset = offset
                offset += self.pfm_kerns_length
            else:
                self.pfm_values['PairKernTable'] = 0
        else:  # order according to PFM doc
            self.pfm_values['Device'] = offset
            self.pfm_offsets['DeviceName'] = offset
            offset += len(self.pfm_values['DeviceName']) + 1
            self.pfm_values['Face'] = offset
            self.pfm_offsets['WindowsName'] = offset
            offset += len(self.pfm_values['WindowsName']) + 1
            self.pfm_values['ExtMetricOffset'] = offset
            self.pfm_ext_offset = offset
            offset += self.pfm_ext_length
            self.pfm_values['ExtentTable'] = offset
            self.pfm_widths_offset = offset
            offset += self.pfm_widths_length
            self.pfm_values['DriverInfo'] = offset
            self.pfm_offsets['PostscriptName'] = offset
            offset += len(self.pfm_values['PostscriptName']) + 1

            if self.pfm_kerns_num > 0:
                self.pfm_values['PairKernTable'] = offset
                self.pfm_kerns_offset = offset
                offset += self.pfm_kerns_length
            else:
                self.pfm_values['PairKernTable'] = 0

            for i in range(self.pfm_extra_values_start, len(self.pfm_names)):
                self.pfm_offsets[self.pfm_names[i]] = offset
                offset += len(self.pfm_values[self.pfm_names[i]]) + 1

        self.calculated_size = offset
        self.pfm_values['Size'] = self.calculated_size

        for i in range(self.pfm_strings_start, len(self.pfm_names)):
            self.pfm_template[self.pfm_names[i]] = f"{1 + len(self.pfm_values[self.pfm_names[i]])}s"

    def make_pfm(self) -> bytes:
        """ Serialize PFM data into binary format of PFM file. """
        content_head = [self.pfm_values[self.pfm_names[i]]
                        for i in range(self.pfm_ext_start)]
        new_pfm = struct.pack(self.pfm_head_template, *content_head)
        if self.verbose:
            print(
                f"HEADER ({hex(len(new_pfm))}):",
                " ".join([hex(v) if isinstance(v, int) else str(v) for v in content_head])
            )

        if PFM_TABLES_ORDER:  # order according Y&Y
            content_ext = [self.pfm_values[self.pfm_names[i]]
                           for i in range(self.pfm_ext_start, self.pfm_strings_start)]
            new_pfm += struct.pack(self.pfm_ext_template, *content_ext)
            if self.verbose:
                print(
                    f"HEAD_EXT  ({hex(len(new_pfm))}):",
                    " ".join([hex(v) if isinstance(v, int) else str(v) for v in content_ext])
                )

            for i in range(self.pfm_strings_start, len(self.pfm_names)):
                new_pfm += struct.pack(self.pfm_template[self.pfm_names[i]],
                                       self.pfm_values[self.pfm_names[i]].encode(STRING_ENCODING))

            new_pfm += struct.pack(self.pfm_widths_template, *self.pfm_widths)

            if self.pfm_kerns_num > 0:
                new_pfm += struct.pack('<H', self.pfm_kerns_num)
                new_pfm += struct.pack(self.pfm_kerns_template, *self.pfm_kerns)
        else:  # order according PFM doc
            for i in range(self.pfm_strings_start, self.pfm_strings_start + 2):
                new_pfm += struct.pack(self.pfm_template[self.pfm_names[i]],
                                       self.pfm_values[self.pfm_names[i]].encode(STRING_ENCODING))

            content_ext = [self.pfm_values[self.pfm_names[i]]
                           for i in range(self.pfm_ext_start, self.pfm_strings_start)]
            new_pfm += struct.pack(self.pfm_ext_template, *content_ext)
            if self.verbose:
                print(
                    f"HEAD_EXT  ({hex(len(new_pfm))}):",
                    " ".join([hex(v) if isinstance(v, int) else str(v) for v in content_ext])
                )

            new_pfm += struct.pack(self.pfm_widths_template, *self.pfm_widths)

            for i in range(self.pfm_strings_start + 2, self.pfm_extra_values_start):
                new_pfm += struct.pack(self.pfm_template[self.pfm_names[i]],
                                       self.pfm_values[self.pfm_names[i]].encode(STRING_ENCODING))

            if self.pfm_kerns_num > 0:
                new_pfm += struct.pack('H', self.pfm_kerns_num)
                new_pfm += struct.pack(self.pfm_kerns_template, *self.pfm_kerns)

            for i in range(self.pfm_extra_values_start, len(self.pfm_names)):
                new_pfm += struct.pack(self.pfm_template[self.pfm_names[i]], self.pfm_values[self.pfm_names[i]])

        if self.calculated_size != len(new_pfm):
            print(f"A2P: Packing PFM went wrong {self.calculated_size}<>{len(new_pfm)}!!!")

        return new_pfm

    def write_output(self, output_file: str):
        with open(output_file, "wb") as out_file:
            out_file.write(self.make_pfm())


class AfmReader:
    """
    Simple AFM file reader, reads AFM and converts it into data structures:
    dict with font properties, and two lists with characters widths and kerns.
    """

    @staticmethod
    def read_afm(afm_filename: str) -> typing.Tuple[dict, list, list]:
        afm_values: typing.Dict[str, str | int | float] = {}
        afm_widths: typing.List[float | None] = [None] * 256
        afm_kerns: typing.List[typing.Tuple[int, int, float]] = []

        with open(afm_filename, "r", encoding=STRING_ENCODING) as afm_file:
            first_line = afm_file.readline()
            if not first_line.startswith("StartFontMetrics"):
                raise RuntimeError("A2P: Not an AFM file (improper header).")

            for line in afm_file:
                fields = line.strip().split()
                if line.startswith("StartCharMetrics"):
                    break
                if fields[0] in AFM_HEADERS_DEFAULTS:
                    afm_values[fields[0]] = fields[1]
                elif line.startswith("PFMParams"):  # obsolete convention
                    afm_values["PFMname"] = fields[2]
                    afm_values["PFMbold"] = fields[3]
                    afm_values["PFMitalic"] = fields[4]
                elif line.startswith("PFM parameters"):
                    if len(fields) >= 4 and fields[3] != "*":
                        afm_values["PFMname"] = fields[3]
                    if len(fields) >= 5 and fields[4] != "*":
                        afm_values["PFMbold"] = fields[4]
                    if len(fields) >= 6 and fields[5] != "*":
                        afm_values["PFMitalic"] = fields[5]
                    if len(fields) >= 7 and fields[6] != "*":
                        afm_values["PFMcharset"] = int(fields[6], 16) if fields[6].startswith("0x") else int(fields[6])
                elif line.startswith("Notice"):
                    afm_values["Notice"] = line[7:].strip()
                elif line.startswith("FontBBox"):
                    afm_values["llx"] = float(fields[1])
                    afm_values["lly"] = float(fields[2])
                    afm_values["urx"] = float(fields[3])
                    afm_values["ury"] = float(fields[4])

            default_char = ""
            first_char = 255
            last_char = 0
            avg_width = 0
            max_width = 0
            afm_codes = {}
            for line in afm_file:
                if line.startswith("EndCharMetrics"):
                    break
                fields = line.strip().split()
                char_code = int(fields[1])
                if char_code >= 0:  # was > 0 !
                    width = float(fields[4])
                    char_name = fields[7]
                    afm_widths[char_code] = width
                    afm_codes[char_name] = char_code
                    if char_code < first_char:
                        first_char = char_code
                    if char_code > last_char:
                        last_char = char_code
                    if width > max_width:
                        max_width = width

                    if char_name == "X":
                        avg_width = width
                    if char_name == "bullet":
                        default_char = char_code
            afm_values["DEFAULT_CHAR"] = default_char
            afm_values["FIRST_CHAR"] = first_char
            afm_values["LAST_CHAR"] = last_char
            afm_values["AVG_WIDTH"] = avg_width
            afm_values["MAX_WIDTH"] = max_width

            for line in afm_file:
                if line.startswith("StartKernPairs"):
                    break
            for line in afm_file:
                if line.startswith("EndKernPairs"):
                    break
                fields = line.strip().split()
                head, char_a, char_b, kern = fields[0], fields[1], fields[2], float(fields[3])

                if head != "KPX":
                    raise ValueError("Malformed AFM kern table")

                if char_a in afm_codes and char_b in afm_codes:
                    afm_kerns.append((afm_codes[char_a], afm_codes[char_b], kern))

        return afm_values, afm_widths, afm_kerns


def main():
    print(f"This is afm2pfm, ver. {VERSION}.")
    parser = argparse.ArgumentParser(description="This is afm2pfm, makes PFM file out of given AFM.")
    parser.add_argument("input", help="Input AFM file")
    parser.add_argument("output", help="Output PFM file")
    parser.add_argument("--nokernlimit", help="Do not obey the limit of 512 kerns", action="store_true")
    parser.add_argument("keyargs", help="Additional key:value arguments", nargs="*")
    args = parser.parse_args()

    extra_args = {}
    for keyvalue in args.keyargs:
        key, value = keyvalue.split(":")
        extra_args[key] = value

    afm_reader = AfmReader()
    afm_values, afm_widths, afm_kerns = afm_reader.read_afm(args.input)

    pfm_writer = PfmWriter()
    pfm_writer.prepare_data(afm_values, afm_widths, afm_kerns, extra_args, args.nokernlimit)
    pfm_writer.calculate_offsets()
    pfm_writer.write_output(args.output)


if __name__ == "__main__":
    main()
