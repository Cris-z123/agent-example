def login(fn):
    def inner(username, context):
        print(f'login{username}')
        fn(username, context)
    return inner

def log(fn):
    def inner(username, context):
        print(f'log{username}')
        fn(username, context)
    return inner

@login
@log
def send(username, context):
    print(f'{username}:{context}')

send('z123', 'hello world')
