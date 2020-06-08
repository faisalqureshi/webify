import util2 as util
import pprint as pp
import copy

class RenderingContext:
    def __init__(self):
        self.logger = util.WebifyLogger.get('rc')
        self.reset()

    def reset(self):
        self.rc = {}
        self.diff_stack = [RenderingContext.empty_diff()]

    @staticmethod
    def empty_diff():
        return {'a': [], 'm': {}, 'd': {}}

    def push(self):
        self.diff_stack.append(RenderingContext.empty_diff())

    def remove(self, keys):
        keys = [keys] if not isinstance(keys, list) else keys
        diff = self.diff_stack[-1]

        for k in keys:
            if k in self.rc.keys():
                if k in diff['a']:
                    diff['a'].remove(k)
                    del self.rc[k]
                elif k in diff['m'].keys():
                    diff['d'][k] = diff['m'][k]
                    del diff['m'][k]
                    del self.rc[k]
                else:
                    diff['d'][k] = copy.deepcopy(self.rc[k])
                    del self.rc[k]

    def add(self, data):
        diff = self.diff_stack[-1]

        for k in data.keys():
            if k in self.rc.keys():
                if k in diff['a']:
                    self.rc[k] = data[k]
                elif k in diff['m'].keys():
                    self.rc[k] = data[k]
                else:
                    diff['m'][k] = copy.deepcopy(self.rc[k])
                    self.rc[k] = data[k]
            else:
                if k in diff['d'].keys():
                    diff['m'][k] = diff['d'][k]
                    del diff['d'][k]
                    self.rc[k] = data[k]
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
    y4 = {'remove': 'this'}

    rc = RenderingContext()
    pp.pprint(rc.diff_stack)
    pp.pprint(rc.data())

    # Case 1
    # rc.push()
    # rc.add(y1)
    # pp.pprint(rc.diff_stack)
    # pp.pprint(rc.data())
    # rc.pop()
    # pp.pprint(rc.diff_stack)
    # pp.pprint(rc.data())

    # Case 2
    # rc.push()
    # rc.add(y1)
    # print('Push and add y1')
    # pp.pprint(rc.diff_stack[-1])
    # pp.pprint(rc.data())
    # rc.push()
    # print('Push and add y2')
    # rc.add(y2)
    # pp.pprint(rc.diff_stack[-1])
    # pp.pprint(rc.data())
    # rc.pop()
    # print('Pop')
    # pp.pprint(rc.diff_stack[-1])
    # pp.pprint(rc.data())
    # rc.pop()
    # print('Pop')
    # pp.pprint(rc.diff_stack[-1])
    # pp.pprint(rc.data())

    # Case 3
    rc.push()
    rc.add({'name': 'John'})
    rc.add({'name': 'Polyani'})
    print('Push and add y1')
    pp.pprint(rc.diff_stack[-1])
    pp.pprint(rc.data())

    # rc.remove('fname')
    # print('Remove fname')
    # pp.pprint(rc.diff_stack[-1])
    # pp.pprint(rc.data())

    rc.push()
    rc.add({'name': 'George'})
    pp.pprint(rc.diff_stack[-1])
    rc.add({'name': 'Grisham'})
    pp.pprint(rc.diff_stack[-1])
    rc.add({'age': 22})
    pp.pprint(rc.diff_stack[-1])
    rc.add({'age': 23})
    pp.pprint(rc.diff_stack[-1])
    rc.add({'age': 34})
    pp.pprint(rc.diff_stack[-1])
    rc.remove('age')
    pp.pprint(rc.diff_stack[-1])
    rc.remove('age')
    pp.pprint(rc.diff_stack[-1])
    rc.remove('name')
    pp.pprint(rc.diff_stack[-1])
    rc.add({'age': 25})
    pp.pprint(rc.diff_stack[-1])
    rc.add({'name': 'Newton'})
    pp.pprint(rc.diff_stack[-1])

#    rc.remove('name')
#    rc.remove('age')
#    rc.remove('name')
    print('Push and add y2')
    pp.pprint(rc.diff_stack[-1])
    pp.pprint(rc.data())

    rc.pop()
    print('Pop')
    pp.pprint(rc.diff_stack[-1])
    pp.pprint(rc.data())

    rc.pop()
    print('Pop')
    pp.pprint(rc.diff_stack[-1])
    pp.pprint(rc.data())



    # rc = RenderingContext()
    # print(rc.diff_stack)
    # rc.add(y1)
    # rc.print()
    # print(rc.diff_stack)
    # print('XXXX')
    # rc.push()
    # rc.add(y2)
    # print('DIFF', rc.diff_stack)
    # rc.add(y3)
    # print('DIFF', rc.diff_stack)
    # rc.add(y3)
    # print('DIFF', rc.diff_stack)
    # rc.print()
    # rc.push()
    # rc.remove({'fname': 'John'})
    # print('DIFF', rc.diff_stack)
    # rc.print()
    # rc.pop()
    # rc.print()
    # rc.pop()
    # rc.print()
    