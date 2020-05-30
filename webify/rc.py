import util2 as util
import pprint as pp
import copy

class RenderingContext:
    def __init__(self):
        self.logger = util.WebifyLogger.get('rc')
        self.rc = {}
        self.diff_stack = [self.empty_diff()]
        
    def empty_diff(self):
        return {'a': [], 'm': {}, 'd': {}}

    def push(self):
        self.diff_stack.append(self.empty_diff())

    def remove(self, data):
        diff = self.diff_stack[-1]

        for k in data.keys():
            if k in self.rc.keys():
                if not (k in diff['m'].keys() or diff['a'] or diff['d'].keys()):
                    diff['d'][k] = copy.deepcopy(self.rc[k])
                del self.rc[k]

    def add(self, data):
        diff = self.diff_stack[-1]

        for k in data.keys():
            if k in self.rc.keys():
                # print('M', k, data[k])
                # if k == 'availability':
                #     print('AA', diff)
                if not (k in diff['m'].keys() or k in diff['a'] or k in diff['d'].keys()):
                    #print('\t', self.rc[k])
                    diff['m'][k] = copy.deepcopy(self.rc[k])
                self.rc[k] = data[k]
                # if k == 'availability':
                #     print('AA', diff)
            else:
                kv = {k: data[k]}
                if not k in diff['a']:
                    diff['a'].append(k)
                self.rc.update(kv)
                
    def pop(self):
        diff = self.diff_stack.pop()
        for k in diff['a']:
            del self.rc[k]
        for k in diff['d'].keys():
            self.rc[k] = diff['d'][k]    
        for k in diff['m'].keys():
            # print('R', k, diff['m'][k])
            self.rc[k] = diff['m'][k]

    def data(self):
        return self.rc

    def keys(self):
        return self.rc.keys()

    def value(self, key):
        try:
            return self.rc[key]
        except:
            return None    

    def print(self):
        pp.pprint(self.rc)

if __name__ == '__main__':
    y1 = {'fname': 'John', 'lname': 'Doe'}
    y2 = {'fname': 'Smith', 'age': 42}
    y3 = {'hello': 'world'}

    rc = RenderingContext()
    print(rc.diff_stack)
    rc.add(y1)
    rc.print()
    print(rc.diff_stack)
    print('XXXX')
    rc.push()
    rc.add(y2)
    print('DIFF', rc.diff_stack)
    rc.add(y3)
    print('DIFF', rc.diff_stack)
    rc.add(y3)
    print('DIFF', rc.diff_stack)
    rc.print()
    rc.push()
    rc.remove({'fname': 'John'})
    print('DIFF', rc.diff_stack)
    rc.print()
    rc.pop()
    rc.print()
    rc.pop()
    rc.print()
    