import jinja2
import argparse


class CodeVisualization:

    def __init__(self):
        self.svg_template = 'svg_template.svg'

    def visualize_instructions(self, code, stack, nr_per_row, output):
        data = {'figs': []}
        y_offset = 0
        max_height = 0
        for nr, line in enumerate(code.split('\n')):
            line = line.strip()
            if len(line) == 0:
                continue
            cmd, value = [x.strip() for x in line.split(' ', 2)]
            if cmd.startswith('push'):
                stack.push(value)
            elif cmd.startswith('pop'):
                stack.pop()
            else:
                print("invalid command {}".format(line))

            vis = StackVisualization()
            stack.nr = nr + 1
            vis.build_stack_vis(stack, True)
            width = vis.data['svg']['w']
            if nr % nr_per_row == 0:
                y_offset += max_height
                max_height = 0
            if vis.data['svg']['h'] > max_height:
                max_height = vis.data['svg']['h']
            data['figs'].append({'x': (nr % nr_per_row)*width,
                                'y': y_offset, 'svg': vis.svg})
        y_offset += max_height
        data['svg'] = {'w': width*nr_per_row, 'h': y_offset}
        temp = Template()
        template = temp.read_template(self.svg_template)
        self.svg = template.render(data=data)
        temp.write(self.svg, output)
        print("done, written to {}".format(output))


class Template:

    def read_template(self, path):
        with open(path, 'r') as r:
            return jinja2.Template(r.read())

    def write(self, svg, path):
        with open(path, "w") as w:
            w.write(svg)


class StackData:

    def __init__(self, nr=None):
        self.esp = -1
        self.ebp = -1
        self.content = []
        self.nr = nr if nr else 0
        self.last_action = ''

    def build_from_list(self, l):
        self.content = l

    def set_esp(self, esp):
        self.esp = esp

    def set_ebp(self, ebp):
        self.ebp = ebp

    def push(self, label):
        self.esp += 1
        self.content.append(label)

    def pop(self):
        self.esp -= 1
        return self.content.pop()


class StackVisualization:

    def __init__(self):
        self.cfg = {
            'stack': {'start_h': 40, 'norm_h': 20, 'w': 70},
            'addr': {'addr_space': 50},
            'labels': {'lab_off_x': 5, 'lab_off_y': 15},
            'esp': {'arrow_length': 20, 'esp_width': 25, 'l_mar_esp': 60},
            'svg': {'margin': 10},
            'template': 'cache_template.svg'}
        self.stack = {}
        self.data = {'stack': self.stack}
        self.svg = None

    def build_stack_vis(self, stack, add_ebp_labels=False):
        content = stack.content
        esp = stack.esp
        ebp = stack.ebp
        nr = stack.nr
        self._build_plain_stack(content, nr)
        if ebp is not None and add_ebp_labels:
            self._add_ebp_labels(ebp)
        if esp is not None:
            self._add_esp_label(esp)

        self._calc_sizes()
        self._generate_svg()

    def _build_plain_stack(self, content, nr):
        stack_height = 0
        self.stack['elements'] = []
        """ add empty rectangle at top """
        if nr:
            stack_label = "Stack {}".format(nr)
        else:
            stack_label = None
        self.stack['elements'].append({
            'y': stack_height,
            'h': self.cfg['stack']['start_h'], 'nr': None,
            'label': stack_label})
        stack_height += self.cfg['stack']['start_h']

        """ add stack rectangles with labels """
        for i, label in enumerate(content):
            rect_h = self.cfg['stack']['norm_h']
            self.stack['elements'].append({
                'y': stack_height, 'nr': i,
                'h': rect_h, 'label': label})
            stack_height += rect_h

        """ add stack dimensions """
        self.stack['h'] = stack_height
        self.stack['w'] = self.cfg['stack']['w']
        for d in ['l', 'r', 't', 'b']:
            self.stack['{}_mar'.format(d)] = 0

        """ add label offset """
        self.stack['lab_off_x'] = self.cfg['labels']['lab_off_x']
        self.stack['lab_off_y'] = self.cfg['labels']['lab_off_y']

    def _add_ebp_labels(self, ebp):
        self.stack['r_mar'] += self.cfg['addr']['addr_space']
        for s in self.stack['elements']:
            if s['nr'] is not None:
                offset = (ebp-s['nr'])*4
                if offset != 0:
                    s['ebp_offset'] = "{}(%ebp)".format(offset)
                else:
                    s['ebp_offset'] = "EBP"

    def _add_esp_label(self, esp):
        self.stack['l_mar'] += self.cfg['esp']['l_mar_esp']
        for s in self.stack['elements']:
            if s['nr'] == esp:
                self.data['esp'] = {
                    'y': s['y'],
                    'x': - self.cfg['esp']['l_mar_esp'],
                    'arrow_y': self.cfg['stack']['norm_h']/2,
                    'arrow_x1': self.cfg['esp']['esp_width'],
                    'arrow_x2': self.cfg['esp']['arrow_length'] +
                    self.cfg['esp']['esp_width']}

    def _calc_sizes(self):
        self.data['svg'] = {
            'w': self.stack['w'] + self.stack['l_mar'] +
            self.stack['r_mar'] + self.cfg['svg']['margin']*2,
            'h': self.stack['h'] + self.stack['t_mar'] +
            self.stack['b_mar'] + self.cfg['svg']['margin']*2,
            'margin': self.cfg['svg']['margin']}

    def _generate_svg(self):
        temp = Template()
        filename = self.cfg['template']
        template = temp.read_template(filename)
        self.svg = template.render(data=self.data)

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='visualize stack')
    parser.add_argument('assembly_file')
    parser.add_argument('-o', '--output', default='out.svg')
    parser.add_argument('-s', '--stacks_per_row', default=4, type=int)
    args = parser.parse_args()

    with open(args.assembly_file, 'r') as r:
        program = r.read()
    stack = StackData()
    code = CodeVisualization()
    code.visualize_instructions(program, stack, args.stacks_per_row, args.output)

