with open('therasik-web-source/Therasik_Component_Browser.html','r',encoding='utf-8') as f:
    c = f.read()
print('Has full nav:', 'top-header-nav' in c)
print('Has page-header:', 'page-header' in c)
print('Has DATA:', 'var DATA=' in c)
print('Has slogan:', 'slogan' in c)
print('Total length:', len(c))
# Check lines 190-250
lines = c.split('\n')
for i, line in enumerate(lines[190:255], 191):
    print(f'{i}|{line[:100]}')
