import jinja2
import argparse
import re


class CodeVisualization:

    def __init__(self):
        self.svg_template = 'svg_template.svg'

    def visualize_instructions(self, code, stack, nr_per_row, output,
            stack_width):
        data = {'figs': []}
        y_offset = 0
        max_height = 0
        for nr, line in enumerate(code.split('\n')):
            line = line.strip()
            if len(line) == 0:
                continue
            m = re.match('\d+:\s*(.*)$', line)
            if m:
                cmd = m.group(1)
            else:
                cmd = line
            cmd, value = [x.strip() for x in cmd.split(' ', 1)]
            done = False
            if cmd.startswith('push'):
                stack.push(value)
                done = True
            elif cmd.startswith('pop'):
                stack.pop()
                done = True
            elif cmd.startswith('mov'):
                dst, src = self._split_value(value)
                if dst == "ebp" and src == 'esp':
                    stack.set_ebp_to_esp()
                    done = True
            elif cmd.startswith('sub'):
                reg, value = self._split_value(value)
                if reg == "esp":
                    stack.sub_esp(value)
                    done = True
            if not done:
                print("invalid command {}".format(line))

            vis = StackVisualization(stack_width)
            stack.nr = nr + 1
            stack.label = line
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
    
    def _split_value(self, value):        
        return [x.strip().lower() for x in value.split(',')]

class Template:

    def read_template(self, path):
        with open(path, 'r') as r:
            return jinja2.Template(r.read())

    def write(self, svg, path):
        with open(path, "w") as w:
            w.write(svg)


class StackData:

    def __init__(self, nr=None, label=None):
        self.esp = -1
        self.ebp = -1
        self.content = []
        self.nr = nr if nr else 0
        self.label = label if label else None
        self.last_action = ''

    def build_from_list(self, l):
        self.content = l

    def set_esp(self, esp):
        self.esp = esp

    def set_ebp(self, ebp):
        self.ebp = ebp
        
    def sub_esp(self, value):
        if value[-1] == 'h':
            value = int(value[:-1], 16)
        else:
            value = int(value)
        print(value)
        frames = int(value/4)
        print(frames)
        for i in range(frames):
            self.push('')        

    def set_ebp_to_esp(self):
        self.ebp = self.esp

    def push(self, label):
        self.esp += 1
        self.content.append(label)

    def pop(self):
        self.esp -= 1
        return self.content.pop()


class StackVisualization:

    def __init__(self, stack_width=70):
        self.cfg = {
            'stack': {'start_h': 40, 'norm_h': 20, 'w': stack_width},
            'addr': {'addr_space': 60},
            'labels': {'lab_off_x': 5, 'lab_off_y': 15},
            'esp': {'arrow_length': 2, 'esp_width': 30, 'l_mar_esp': 40},
            'svg': {'margin': 10},
            'template': 'cache_template.svg'}
        self.stack = {}
        self.data = {'stack': self.stack}
        self.svg = None
        self.DOTS_LABEL = "(...)"

    def build_stack_vis(self, stack, add_ebp_labels=False):
        content = stack.content
        esp = stack.esp
        ebp = stack.ebp
        nr = stack.nr
        label = stack.label
        self._build_plain_stack(content, nr, label)
        if ebp is not None and add_ebp_labels:
            self._add_ebp_labels(ebp)
        if esp is not None:
            self._add_esp_label(esp)

        self._calc_sizes()
        self._generate_svg()

    def _build_plain_stack(self, content, nr=None, label=None):
        stack_height = 0
        self.stack['elements'] = []
        """ add empty rectangle at top """
        if label:
            stack_label = label
        elif nr:
            stack_label = "Stack {}".format(nr)
        else:
            stack_label = None
        self.stack['elements'].append({
            'y': stack_height,
            'h': self.cfg['stack']['start_h'], 'nr': None,
            'label': stack_label})
        stack_height += self.cfg['stack']['start_h']

        """ add stack rectangles with labels """        
        status = None
        for i, label in enumerate(content):
        
            # check if empty range
            if i > 0 and i+1 < len(content):
                if label and status != "dots":
                    status = None
                elif not label and status is None:
                    status = "pre"
                elif not label and status == "pre":
                    label = self.DOTS_LABEL
                    status = "dots"                
                elif not label and (status == "dots" or status == "skip") and len(content[i+1]) > 0:
                    print("after")
                    status = "after"
                elif not label:
                    status = "skip"
                    
            if status == "skip" and i+1 < len(content):                
                continue
        
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
                if s['label'] == self.DOTS_LABEL:
                    s['ebp_offset'] = self.DOTS_LABEL
                    continue
                offset = (ebp-s['nr'])*4
                if offset != 0:
                    sign = "+" if ebp > 0 else ""
                    s['ebp_offset'] = "[ebp {}{}]".format(sign,offset)
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='visualize stack')
    parser.add_argument('assembly_file')
    parser.add_argument('-o', '--output', default='out.svg')
    parser.add_argument('-s', '--stacks_per_row', default=4, type=int)
    parser.add_argument('-w', '--stack_width', default=70, type=int)
    args = parser.parse_args()

    with open(args.assembly_file, 'r') as r:
        program = r.read()
    stack = StackData()
    code = CodeVisualization()
    code.visualize_instructions(program, stack, args.stacks_per_row,
                                args.output, args.stack_width)
