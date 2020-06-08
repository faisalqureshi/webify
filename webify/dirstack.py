class DirStack:
    def __init__(self):
        self.dir_list_stack = [DirStack.empty_dir_list()]

    @staticmethod
    def empty_dir_list(name=""):
        return (name, [])

    def push(self, name):
        self.dir_list_stack.append(DirStack.empty_dir_list(name))
    
    def pop(self):
        self.dir_list_stack.pop()

    def top(self):
        return self.dir_list_stack[-1]
        