import sys
import math
import struct

PFM_TABLES_ORDER = 1

pfm_header = []
pfm_head_length = 0
pfm_head_template = ''
pfm_names = []
pfm_template = {}
pfm_offset = {}

pfm_values = {}

pfm_ext_start = 0
pfm_ext_offset = 0
pfm_ext_length = 0
pfm_ext_template = ''
pfm_strings_start = 0
pfm_extravalues_start = 0

afm_headers = {}
weight = {}

pat_len = {}

afm_values = {}
afm_widths = [None] * 2000
afm_codes = {}
afm_names = {}
first_char = 0
last_char = 0
max_width = 0
avg_width = 0
default_char = ""
afm_kerns = []
new_size = 0
no_kern_limit = 0
keyargs = {}


def initialize():
    global pat_len
    pat_len = {'B': 1, 'h': 2, 'H': 2, 'I': 4, '60s': 60}
    struct_pfm_header()
    struct_pfm_extmetric()
    struct_pfm_strings()
    magic_numbers()
    fafm_names()


def struct_pfm_header():
    global pfm_header, pfm_head_length, pfm_head_template, pfm_names, pfm_template, pfm_offset

    pfm_header = [
        ('H',   'Version'),
        ('I',   'Size'),
        ('60s', 'Copyright'),
        ('H',   'Type'),
        ('H',   'Points'),
        ('H',   'VertRes'),
        ('H',   'HorizRes'),
        ('H',   'Ascent'),
        ('H',   'InternalLeading'),
        ('H',   'ExternalLeading'),
        ('B',   'Italic'),
        ('B',   'Underline'),
        ('B',   'Stikeout'),
        ('H',   'Weight'),
        ('B',   'CharSet'),
        ('H',   'PixWidth'),
        ('H',   'PixHeight'),
        ('B',   'PitchAndFamily'),
        ('H',   'AvgWidth'),
        ('H',   'MaxWidth'),
        ('B',   'FirstChar'),
        ('B',   'LastChar'),
        ('B',   'DefaultChar'),
        ('B',   'BreakChar'),
        ('H',   'WidthBytes'),
        ('I',   'Device'),
        ('I',   'Face'),
        ('I',   'BitsPointer'),
        ('I',   'BitsOffset'),
        ('H',   'SizeFields'),
        ('I',   'ExtMetricOffset'),
        ('I',   'ExtentTable'),
        ('I',   'OriginTable'),
        ('I',   'PairKernTable'),
        ('I',   'TrackKernTable'),
        ('I',   'DriverInfo'),
        ('I',   'Reserved')
    ]

    pfm_head_length = 0
    pfm_head_template = '<'
    for i in pfm_header:
        pfm_names.append(i[1])
        pfm_template[i[1]] = i[0]
        pfm_head_template += i[0]
        pfm_offset[i[1]] = pfm_head_length
        pfm_head_length += pat_len[i[0]]


def struct_pfm_extmetric():
    global pfm_ext_start, pfm_ext_offset, pfm_ext_length, pfm_ext_template, pfm_names, pfm_template, pfm_offset, pat_len

    pfm_extmetric = [
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

    pfm_ext_start = len(pfm_names)
    pfm_ext_offset = pfm_head_length + 1
    pfm_ext_length = 0
    pfm_ext_template = '<'

    for i in pfm_extmetric:
        pfm_names.append(i[1])
        pfm_template[i[1]] = i[0]
        pfm_ext_template += i[0]
        pfm_offset[i[1]] = pfm_ext_offset + pfm_ext_length
        pfm_ext_length += pat_len[i[0]]


def struct_pfm_strings():
    global pfm_strings_start, pfm_extravalues_start, pfm_names

    pfm_strings = [
        ('Device',     'DeviceName'),
        ('Face',       'WindowsName'),
        ('DriverInfo', 'PostscriptName')
    ]

    pfm_strings_start = len(pfm_names)

    for i in pfm_strings:
        pfm_names.append(i[1])

    pfm_extravalues_start = len(pfm_names)


def fafm_names():
    global afm_headers, weight

    afm_headers = {
        'FontName': 'FontAnna',
        'Weight': weight['Regular'],
        'ItalicAngle': 0,
        'IsFixedPitch': 'false',
        'CapHeight': 750,
        'XHeight': 400,
        'Descender': -250,
        'Ascender': 750,
        'UnderlinePosition': -200,
        'UnderlineThickness': 40,
        'EncodingScheme': 'FontSpecific',  # not used
        'Version': '0.000',  # not used
        'FullName': 'FontAnna',  # not used
        'FamilyName': 'FontAnna'  # not used
    }


def magic_numbers():
    global weight

    weight['Light'] = 300
    weight['Regular'] = weight['Normal'] = weight['Book'] = 400
    weight['Medium'] = weight['Demi'] = 500
    weight['Bold'] = 700
    weight['Black'] = 1000


def read_afm(afm_file):
    global afm_headers, afm_values, first_char, last_char, max_width, afm_widths, afm_codes, afm_names, avg_width, default_char, afm_kerns

    first_line = afm_file.readline()
    if not first_line.startswith("StartFontMetrics"):
        print("A2P: Not an AFM file")

    for line in afm_file:
        fields = line.strip().split()
        if line.startswith("StartCharMetrics"):
            break
        if fields[0] in afm_headers:
            afm_values[fields[0]] = fields[1]
        if line.startswith("PFMParams"):  # obsolete convention
            afm_values["PFMname"] = fields[2]
            afm_values["PFMbold"] = fields[3]
            afm_values["PFMitalic"] = fields[4]
        if line.startswith("PFM parameters"):
            if len(fields) >= 4 and fields[3] != "*":
                afm_values["PFMname"] = fields[3]
            if len(fields) >= 5 and fields[4] != "*":
                afm_values["PFMbold"] = fields[4]
            if len(fields) >= 6 and fields[5] != "*":
                afm_values["PFMitalic"] = fields[5]
            if len(fields) >= 7 and fields[6] != "*":
                afm_values["PFMcharset"] = int(fields[6], 0)

        if line.startswith("Notice"):
            afm_values["Notice"] = line[7:].strip()

        if line.startswith("FontBBox"):
            afm_values["llx"] = fields[1]
            afm_values["lly"] = fields[2]
            afm_values["urx"] = fields[3]
            afm_values["ury"] = fields[4]

    first_char = 255
    last_char = 0
    max_width = 0

    for line in afm_file:
        if line.startswith("EndCharMetrics"):
            break
        fields = line.strip().split()
        char_code = int(float(fields[1]))
        if char_code > 0:
            width = round(float(fields[4]))
            char_name = fields[7]
            afm_widths[char_code] = width
            afm_codes[char_name] = char_code
            afm_names[char_code] = char_name
            if char_code < first_char:
                first_char = char_code
            if char_code > last_char:
                last_char = char_code
            if width > max_width:
                max_width = width

            if char_name == "X":
                avg_width = width
            if char_name == "bullet" and char_code >= 0:
                default_char = char_code

    for line in afm_file:
        if line.startswith("StartKernPairs"):
            break

    if not afm_file.closed:
        for line in afm_file:
            if line.startswith("EndKernPairs"):
                break
            fields = line.strip().split()
            dummy, chara, charb, kern = fields[0], fields[1], fields[2], int(float(fields[3]))

            if dummy != "KPX":
                raise ValueError("Malformed AFM kern table")

            if chara in afm_codes and charb in afm_codes:
                afm_kerns.append([afm_codes[chara], afm_codes[charb], kern])


def prepare_data():
    global afm_headers, afm_values, keyargs, weight, pfm_ext_length, pfm_values

    def rounds(x):
        return round(float(x))

    def ceiling(x):
        return int(math.ceil(float(x)))

    def floor(x):
        return int(math.floor(float(x)))

    pfm_values['Version'] = 256
    pfm_values['Type'] = 129
    pfm_values['Points'] = 10
    pfm_values['VertRes'] = 300
    pfm_values['HorizRes'] = 300
    pfm_values['ExternalLeading'] = 0
    pfm_values['Underline'] = 0
    pfm_values['Stikeout'] = 0
    pfm_values['WidthBytes'] = 0
    pfm_values['BitsPointer'] = 0
    pfm_values['BitsOffset'] = 0
    pfm_values['SizeFields'] = 30
    pfm_values['OriginTable'] = 0
    pfm_values['TrackKernTable'] = 0
    pfm_values['Reserved'] = 0
    pfm_values['Size_ext'] = pfm_ext_length
    pfm_values['PointSize'] = 200
    pfm_values['Orientation'] = 0
    pfm_values['MasterHeight'] = 1000
    pfm_values['MinScale'] = 4
    pfm_values['MaxScale'] = 900
    pfm_values['MasterUnits'] = 1000
    pfm_values['KernTracks'] = 0
    pfm_values['DeviceName'] = 'PostScript'

    for i in afm_headers:
        if i not in afm_values:
            print(f"Missing AFM value: {i}, assuming: {afm_headers[i]}.")
            afm_values[i] = afm_headers[i]

    pfm_values['PostscriptName'] = afm_values['FontName']
    pfm_values['Copyright'] = (afm_values['Notice'] + ' ' * 60)[:60].encode()
    pfm_values['Ascent'] = ceiling(afm_values['ury'])
    pfm_values['InternalLeading'] = max(0, ceiling(afm_values['ury']) - floor(afm_values['lly']) - 1000)
    pfm_values['Italic'] = 1 if float(afm_values['ItalicAngle']) != 0 else 0

    pfm_values['Weight'] = weight[afm_values['FontName'].split('-')[-1]] if afm_values['FontName'].split('-')[-1] in weight else weight['Regular']
    pfm_values['CharSet'] = 255
    pfm_values['PixWidth'] = max(0, ceiling(afm_values['urx']) - floor(afm_values['llx']))
    pfm_values['PixHeight'] = 1000 + rounds(pfm_values['InternalLeading'])
    pfm_values['PitchAndFamily'] = 16 * 1 + (0 if afm_values['IsFixedPitch'] == 'true' else 1)
    pfm_values['AvgWidth'] = rounds(avg_width) if avg_width else 500
    pfm_values['MaxWidth'] = rounds(max_width)
    pfm_values['FirstChar'] = 0
    pfm_values['LastChar'] = 255
    pfm_values['DefaultChar'] = (default_char if default_char else ord('?')) - pfm_values['FirstChar']
    pfm_values['BreakChar'] = ord(' ') - pfm_values['FirstChar']
    pfm_values['CapHeight'] = rounds(afm_values['CapHeight'])
    pfm_values['XHeight'] = rounds(afm_values['XHeight'])
    pfm_values['LowerCaseAscent'] = rounds(afm_values['Ascender'])
    pfm_values['LowerCaseDescent'] = rounds(-float(afm_values['Descender']))
    pfm_values['Slant'] = rounds(10 * float(afm_values['ItalicAngle']))
    pfm_values['SuperScript'] = - rounds(0.8 * float(pfm_values['XHeight']))
    pfm_values['SubScript'] = rounds(0.3 * float(pfm_values['XHeight']))
    pfm_values['SuperScriptSize'] = 800
    pfm_values['SubScriptSize'] = 800
    pfm_values['UnderlineOffset'] = rounds(-float(afm_values['UnderlinePosition']))
    pfm_values['UnderlineWidth'] = rounds(afm_values['UnderlineThickness'])
    pfm_values['DoubleUpperUnderlineOffset'] = rounds(pfm_values['UnderlineOffset'])
    pfm_values['DoubleLowerUnderlineOffset'] = rounds(
        float(pfm_values['DoubleUpperUnderlineOffset'])
        + 3 * float(pfm_values['UnderlineWidth']))
    pfm_values['DoubleUpperUnderlineWidth'] = rounds(pfm_values['UnderlineWidth'])
    pfm_values['DoubleLowerUnderlineWidth'] = rounds(pfm_values['UnderlineWidth'])
    pfm_values['StrikeOutOffset'] = rounds(0.6 * float(pfm_values['XHeight']))
    pfm_values['StrikeOutWidth'] = rounds(pfm_values['UnderlineWidth'])

    if 'PFMname' in afm_values:
        pfm_values['WindowsName'] = afm_values['PFMname']
    else:
        pfm_values['WindowsName'] = afm_values['FontName']
        # / ([Oo]bli(que)? |[Ii]t(alic)? |[Kk]ursywa |[Ss]lant(ed)? | Lt |[Ll]ight |[Rr]eg(ular)? |[Nn] or (mal)? | Bk |[Bb]ook | Dm |[Dd]emi | Md |[Mm]edium | Bd |[Bb]old | Blk |[Bb]lack |[\ _\-:])$ // gx){}
        # TODO: remove sufixes
        while any(x in pfm_values['WindowsName'] for x in ['Obli', 'obli', 'It', 'it', 'Kursywa', 'kursywa', 'Slant', 'slant', 'Lt', 'Light', 'Reg', 'reg', 'Nor', 'nor', 'Bk', 'Book', 'Dm', 'dm', 'Md', 'md', 'Bd', 'bd', 'Blk', 'blk', ' ', '_', '-']):
            pfm_values['WindowsName'] = pfm_values['WindowsName'][:-1]

    if 'PFMbold' in afm_values:
        pfm_values['Weight'] = rounds(afm_values['PFMbold']) if float(afm_values['PFMbold']) > 10 else (
            weight['Regular'] if float(afm_values['PFMbold']) == 0 else weight['Bold']
        )

    if 'PFMitalic' in afm_values:
        pfm_values['Italic'] = 0 if float(afm_values['PFMitalic']) == 0 else 1

    if 'PFMcharset' in afm_values:
        pfm_values['CharSet'] = int(afm_values['PFMcharset'])

    prepare_widths()
    prepare_kerns()

    put_extra_values('Info', 'JNSteam')

    for i in keyargs:
        if i in pfm_values:
            pfm_values[i] = keyargs[i]
        else:
            raise ValueError(f"Unknown key in command line parameter {i}")


def prepare_widths():
    global pfm_widths_num, pfm_widths_length, pfm_widths_template, pfm_widths, pfm_values
    pfm_widths_num = pfm_values['LastChar'] - pfm_values['FirstChar'] + 1
    pfm_widths_length = pfm_widths_num * 2
    pfm_widths_template = 'H' * pfm_widths_num
    pfm_widths = []

    for i in range(pfm_values['FirstChar'], pfm_values['LastChar'] + 1):
        if afm_widths[i] is not None:
            pfm_widths.append(round(afm_widths[i]))
        else:
            pfm_widths.append(pfm_values['AvgWidth'])


def prepare_kerns():
    global pfm_kerns_num, pfm_values, pfm_kerns_length, pfm_kerns_template, pfm_kerns, afm_kerns, no_kern_limit

    if len(afm_kerns) > 0:
        if len(afm_kerns) > 511:
            if no_kern_limit:
                print('A2P: The number of kerns is', len(afm_kerns), "(more than allowed 512)")
            else:
                afm_kerns.sort(key=lambda x: abs(x[2]), reverse=True)
                deleted = afm_kerns[512:]
                afm_kerns = afm_kerns[:512]
                print('A2P: The number of kerns reduced by', len(deleted), ' (values <=', abs(deleted[0][2]), "deleted)")

        afm_kerns.sort(key=lambda x: (x[1], x[0]))
        pfm_kerns_num = len(afm_kerns)
        pfm_values['KernPairs'] = pfm_kerns_num
        pfm_kerns_length = pfm_kerns_num * 4 + 2  # +2 for undocumented length of kern table
        pfm_kerns_template = "<" + 'BBh' * pfm_kerns_num
        pfm_kerns = []

        for i in afm_kerns:
            pfm_kerns.extend([i[0], i[1], i[2]])

    else:
        pfm_kerns_num = 0
        pfm_values['KernPairs'] = 0


def put_extra_values(name, value):
    global pfm_names, pfm_values, pfm_template
    pfm_names.append(name)
    pfm_values[name] = value
    pfm_template[name] = f"{1 + len(value)}s"


def calculate_offsets():
    global pfm_head_length, pfm_ext_length, pfm_ext_offset, pfm_offset, pfm_names, pfm_values, pfm_widths_offset, pfm_widths_length, pfm_kerns_num, pfm_kerns_offset, pfm_kerns_length, pfm_template, new_size
    start = 0
    start += pfm_head_length

    if PFM_TABLES_ORDER:  # order according to Y&Y
        pfm_values['ExtMetricOffset'] = start
        pfm_ext_offset = start
        start += pfm_ext_length
        pfm_values['Device'] = start
        pfm_offset['DeviceName'] = start
        start += len(pfm_values['DeviceName']) + 1
        pfm_values['Face'] = start
        pfm_offset['WindowsName'] = start
        start += len(pfm_values['WindowsName']) + 1
        pfm_values['DriverInfo'] = start
        pfm_offset['PostscriptName'] = start
        start += len(pfm_values['PostscriptName']) + 1

        for i in range(pfm_extravalues_start, len(pfm_names)):
            pfm_offset[pfm_names[i]] = start
            start += len(pfm_values[pfm_names[i]]) + 1

        pfm_values['ExtentTable'] = start
        pfm_widths_offset = start
        start += pfm_widths_length

        if pfm_kerns_num > 0:
            pfm_values['PairKernTable'] = start
            pfm_kerns_offset = start
            start += pfm_kerns_length
        else:
            pfm_values['PairKernTable'] = 0
    else:  # order according to PFM doc
        pfm_values['Device'] = start
        pfm_offset['DeviceName'] = start
        start += len(pfm_values['DeviceName']) + 1
        pfm_values['Face'] = start
        pfm_offset['WindowsName'] = start
        start += len(pfm_values['WindowsName']) + 1
        pfm_values['ExtMetricOffset'] = start
        pfm_ext_offset = start
        start += pfm_ext_length
        pfm_values['ExtentTable'] = start
        pfm_widths_offset = start
        start += pfm_widths_length
        pfm_values['DriverInfo'] = start
        pfm_offset['PostscriptName'] = start
        start += len(pfm_values['PostscriptName']) + 1

        if pfm_kerns_num > 0:
            pfm_values['PairKernTable'] = start
            pfm_kerns_offset = start
            start += pfm_kerns_length
        else:
            pfm_values['PairKernTable'] = 0

        for i in range(pfm_extravalues_start, len(pfm_names)):
            pfm_offset[pfm_names[i]] = start
            start += len(pfm_values[pfm_names[i]]) + 1

    new_size = start
    pfm_values['Size'] = new_size

    for i in range(pfm_strings_start, len(pfm_names)):
        pfm_template[pfm_names[i]] = f"{1 + len(pfm_values[pfm_names[i]])}s"


def make_pfm():
    global pfm_ext_start, pfm_names, pfm_values, pfm_head_template, pfm_strings_start, pfm_template, pfm_ext_template, pfm_widths_template, pfm_widths, pfm_kerns_num, pfm_kerns_template, pfm_kerns, pfm_extravalues_start, new_size

    content_h = [pfm_values[pfm_names[i]] for i in range(pfm_ext_start)]
    new_pfm = struct.pack(pfm_head_template, *content_h)
    print(" ".join([hex(v) if isinstance(v, int) else str(v) for v in content_h]))

    if PFM_TABLES_ORDER:  # order according Y&Y
        content_x = [pfm_values[pfm_names[i]] for i in range(pfm_ext_start, pfm_strings_start)]
        new_pfm += struct.pack(pfm_ext_template, *content_x)
        print(" ".join([hex(v) if isinstance(v, int) else str(v) for v in content_x]))

        for i in range(pfm_strings_start, len(pfm_names)):
            new_pfm += struct.pack(pfm_template[pfm_names[i]], pfm_values[pfm_names[i]].encode())

        new_pfm += struct.pack(pfm_widths_template, *pfm_widths)

        if pfm_kerns_num > 0:
            new_pfm += struct.pack('H', pfm_kerns_num)
            new_pfm += struct.pack(pfm_kerns_template, *pfm_kerns)
    else:  # order according PFM doc
        for i in range(pfm_strings_start, pfm_strings_start + 2):
            new_pfm += struct.pack(pfm_template[pfm_names[i]], pfm_values[pfm_names[i]])

        content_x = [pfm_values[pfm_names[i]] for i in range(pfm_ext_start, pfm_strings_start)]
        new_pfm += struct.pack(pfm_ext_template, *content_x)

        new_pfm += struct.pack(pfm_widths_template, *pfm_widths)

        for i in range(pfm_strings_start + 2, pfm_extravalues_start):
            new_pfm += struct.pack(pfm_template[pfm_names[i]], pfm_values[pfm_names[i]].encode())

        if pfm_kerns_num > 0:
            new_pfm += struct.pack('H', pfm_kerns_num)
            new_pfm += struct.pack(pfm_kerns_template, *pfm_kerns)

        for i in range(pfm_extravalues_start, len(pfm_names)):
            new_pfm += struct.pack(pfm_template[pfm_names[i]], pfm_values[pfm_names[i]])

    if new_size != len(new_pfm):
        print(f'A2P: Packing PFM went wrong {new_size}<>{len(new_pfm)}!!!')

    return new_pfm


def main():
    global no_kern_limit, keyargs
    print("This is afm2pfm, ver. 0.20")
    initialize()

    infile = sys.argv[1]
    outfile = sys.argv[2]
    no_kern_limit = 0
    keyargs = {}

    for i in sys.argv[3:]:
        if i in ("--nokernlimit", "nokernlimit"):
            no_kern_limit = 1  # don't obey the limit of 512 kerns
        elif ":" in i:
            key, value = i.split(":", 1)
            keyargs[key] = value

    with open(infile, "r") as afm_file:
        read_afm(afm_file)

    prepare_data()
    calculate_offsets()

    with open(outfile, "wb") as out_file:
        out_file.write(make_pfm())


if __name__ == "__main__":
    main()
