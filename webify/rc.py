import util2 as util
import pprint as pp
import copy

class RenderingContext:
    def __init__(self):
        self.logger = util.WebifyLogger.get('rc')
        self.rc = {}
        self.diff_stack = [self.diff()]

    def data(self):
        return self.rc
        
    def diff(self):
        return {'a': [], 'm': []}
        
    def push(self):
        self.diff_stack.append(self.diff())

    def add(self, data):
        diff = self.diff_stack[-1]

        for k in data.keys():
            if k in self.rc.keys():
                diff['m'].append({k: copy.deepcopy(self.rc[k])})
                self.rc[k] = data[k]
            else:
                kv = {k: data[k]}
                diff['a'].append({k: data[k]})
                self.rc.update(kv)
                
    def pop(self):
        diff = self.diff_stack.pop()
        for i in diff['a']:
            for k in i.keys():
                del self.rc[k]
        for i in diff['m']:
            for k in i.keys():
                self.rc[k] = i[k]

    def get(self):
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

    rc = RenderingContext()
    rc.add(y1)
    rc.print()
    rc.push()
    rc.add(y2)
    rc.print()
    rc.pop()
    rc.print()
    