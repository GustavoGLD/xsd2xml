#!/usr/bin/python3

from argparse import ArgumentParser
import configparser
import xmlschema
from xmlschema.validators import (
    XsdElement,
    XsdAnyElement,
    XsdComplexType,
    XsdAtomicBuiltin,
    XsdSimpleType,
    XsdList,
    XsdUnion,
    XsdGroup,
)

# default tag value
UKN_VALUE = 'UNKNOWN'

DEFAULT_SCHEMAS = {
    '': 'http://www.iata.org/IATA/2015/00/2020.2/{0}',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'xsi:schemaLocation': "http://www.iata.org/IATA/2015/00/2020.2/{0} ../{0}.xsd"
}

# sample data is hardcoded
def valsmap(v):
    # numeric types
    v['decimal']    = '10'
    v['float']      = '-42.217E11'
    v['double']     = '+24.3e-3'
    v['integer']    = '176'
    v['positiveInteger'] = '+3'
    v['negativeInteger'] = '-7'
    v['nonPositiveInteger'] = '-34'
    v['nonNegativeInteger'] = '35'
    v['long'] = '567'
    v['int'] = '109'
    v['short'] = '4'
    v['byte'] = '2'
    v['unsignedLong'] = '94'
    v['unsignedInt'] = '96'
    v['unsignedShort'] = '24'
    v['unsignedByte'] = '17'
    # time/duration types
    v['dateTime'] = '2020-12-17T09:30:47Z'
    v['date'] = '2020-04-12'
    v['gYearMonth'] = '2020-04'
    v['gYear'] = '2020'
    v['duration'] = 'P2Y6M5DT12H35M30S'
    v['dayTimeDuration'] = 'P1DT2H'
    v['yearMonthDuration'] = 'P2Y6M'
    v['gMonthDay'] = '--04-12'
    v['gDay'] = '---02'
    v['gMonth'] = '--04'
    # string types
    v['string'] = 'String'
    v['normalizedString'] = 'The cure for boredom is curiosity.'
    v['token'] = 'token'
    v['language'] = 'en-US'
    v['NMTOKEN'] = 'A_BCD'
    v['NMTOKENS'] = 'ABCD 123'
    v['NCName'] = '_my.Element'
    # magic types
    v['ID'] = 'IdID'
    v['IDREFS'] = 'IDrefs'
    v['ENTITY'] = 'prod557'
    v['ENTITIES'] = 'prod557 prod563'
    # oldball types
    v['QName'] = 'pre:myElement'
    v['boolean'] = 'true'
    v['hexBinary'] = '0FB8'
    v['base64Binary'] = '0fb8'
    v['anyURI'] = 'https://mixvel.com/'
    v['notation'] = 'notation'

class GenXML:
    def __init__(self, xsd, elem, template, use_default_schemas, enable_choice, print_comments):
        self.xsd = xmlschema.XMLSchema(xsd)
        self.elem = elem
        self.template = template
        self.use_default_schemas = use_default_schemas
        self.enable_choice = enable_choice
        self.print_comments = print_comments
        self.root = True
        self.vals = {}

    # read template text values for tags
    def read_template(self):
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(self.template)
        if config.has_section(self.elem):
            for key in config[self.elem]:
                self.vals[key] = config[self.elem].get(key)

    # shorten the namespace
    def short_ns(self, ns):
        for k, v in self.xsd.namespaces.items():
            if v == ns:
                return k
        return ''

    # if name is using long namespace,
    # lets replace it with the short one
    def use_short_ns(self, name):
        if name[0] == '{':
            x = name.find('}')
            ns = name[1:x]
            short_ns = self.short_ns(ns)
            return short_ns + ":" + name[x + 1:] if short_ns != '' else name[x + 1:]
        return name

    # remove the namespace in name
    def remove_ns(self, name):
        if name[0] == '{':
            x = name.find('}')
            return name[x + 1:]
        return name

    # header of xml doc
    def print_header(self):
        print("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")

    # put all defined namespaces as a string
    def ns_map_str(self):
        ns_all = ''
        s = self.xsd.namespaces if self.use_default_schemas else DEFAULT_SCHEMAS
        for k, v in s.items():
            if ns_all.find(v) == -1:
                prefix = k
                if prefix.find(':') == -1 or prefix == '':
                    prefix = 'xmlns' + (':' + prefix if prefix != '' else '')
                ns_all += prefix + '=\"' + v.format(self.elem) + '\"' + ' '
        return ns_all.strip()

    # start a tag with name
    def start_tag(self, name, attrs=''):
        x = '<' + name
        if self.root:
            self.root = False
            x += ' ' + self.ns_map_str()
        if attrs:
            x += ' ' + attrs
        x += '>'
        return x

    # end a tag with name
    def end_tag(self, name):
        return '</' + name + '>'

    # make a sample data for primitive types
    def genval(self, name):
        name = self.remove_ns(name)
        if name in self.vals:
            return self.vals[name]
        return UKN_VALUE

    # make attributes string
    def gen_attrs(self, attributes):
        a_all = ''
        for attr in attributes:
            tp = attributes[attr].type.name
            a_all += attr + '="' + self.genval(tp) + '" '
        return a_all.strip()

    # print a group
    def group2xml(self, g):
        model = str(g.model)
        model = self.remove_ns(model)
        nextg = g._group
        y = len(nextg)
        if y == 0:
            self.print_comment('empty')
            return
    
        self.print_comment('START:[' + model + ']')
        if self.enable_choice and model == 'choice':
            self.print_comment('next item is from a [choice] group with size=' + str(y) + '')
        else:
            self.print_comment('next ' + str(y) + ' items are in a [' + model + '] group')
            
        for ng in nextg:
            if isinstance(ng, XsdElement):
                self.node2xml(ng)
            elif isinstance(ng, XsdAnyElement):
                self.node2xml(ng)
            else:
                self.group2xml(ng)
        
            if self.enable_choice and model == 'choice':
                break
        self.print_comment('END:[' + model + ']')
    
    # print a node
    def node2xml(self, node):
        if int(node.min_occurs or 1) == 0:
            self.print_comment('next 1 item is optional (minOccurs = 0)')
        if int(node.max_occurs or 1) > 1:
            self.print_comment('next 1 item is multiple (maxOccurs > 1)')
        
        if isinstance(node, XsdAnyElement):
            print('<_ANY_/>')
            return

        if isinstance(node.type, XsdComplexType):
            n = self.use_short_ns(node.name)
            if node.type.is_simple():
                self.print_comment('simple content')
                tp = str(type(node.type.content))
                print(self.start_tag(n) + self.genval(tp) + self.end_tag(n))
            elif not isinstance(node.type.content, XsdGroup):
                self.print_comment('complex content')
                attrs = self.gen_attrs(node.attributes)
                tp = node.type.content.name
                print(self.start_tag(n, attrs) + self.genval(tp) + self.end_tag(n))
            else:
                self.print_comment('complex content')
                print(self.start_tag(n))
                self.group2xml(node.type.content)
                print(self.end_tag(n))

        elif isinstance(node.type, XsdAtomicBuiltin):
            n = self.use_short_ns(node.name)
            tp = str(node.type)
            print(self.start_tag(n) + self.genval(tp) + self.end_tag(n))
        elif isinstance(node.type, XsdSimpleType):
            n = self.use_short_ns(node.name)
            if isinstance(node.type, XsdList):
                self.print_comment('simpletype: list')
                tp = str(node.type.item_type)
                print(self.start_tag(n) + self.genval(tp) + self.end_tag(n))
            elif isinstance(node.type, XsdUnion):
                self.print_comment('simpletype: union.')
                self.print_comment('default: using the 1st type')
                tp = str(node.type.member_types[0].base_type)
                print(self.start_tag(n) + self.genval(tp) + self.end_tag(n))
            else:
                tp = node.type.base_type.name
                value = self.genval(n)
                if value == UKN_VALUE:
                    value = self.genval(tp)
                print(self.start_tag(n) + value + self.end_tag(n))
        else:
            print('ERROR: unknown type: ' + node.type)
    
    def print_comment(self, comment):
        if self.print_comments:
            print('<!--' + comment + '-->')

    # setup and print everything
    def run(self):
        valsmap(self.vals)
        if self.template:
            self.read_template()
        self.print_header()
        self.node2xml(self.xsd.elements[self.elem])

def main():
    parser = ArgumentParser()
    parser.add_argument("-s", "--schema", dest="xsdfile", required=True, 
                        help="select the xsd used to generate xml")
    parser.add_argument("-e", "--element", dest="element", required=True,
                        help="select an element to dump xml")
    parser.add_argument("-t", "--template", dest="template",
                        help="template for tag content")
    parser.add_argument("-d", "--default_namespaces", dest="use_default_namespaces", default=False, action="store_true",
                        help="use default namespaces for xml generation")
    parser.add_argument("-c", "--choice",
                        action="store_true", dest="enable_choice", default=False,
                        help="enable the <choice> mode")
    parser.add_argument("-p", "--print_comments", dest="print_comments", default=False,
                        help="print comments to result xml")
    args = parser.parse_args()

    generator = GenXML(args.xsdfile, args.element, args.template, args.use_default_namespaces, args.enable_choice, args.print_comments)
    generator.run()

if __name__ == "__main__":
    main()
