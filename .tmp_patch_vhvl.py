with open('api/static/console.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find setOutput(""); near line 5470 in runVhvlHumanization
target = '  setOutput("");\n'
insert_idx = None
for i in range(5465, 5480):
    if lines[i] == target:
        insert_idx = i
        break

if insert_idx is None:
    print("Not found in 5465-5480, searching wider...")
    for i in range(5400, 5550):
        if lines[i] == target:
            print(f"  Found at {i}: {repr(lines[i-1][:60])}")

if insert_idx is not None:
    lines.insert(insert_idx, '  window.__vhvlLastVH = vh;   // saved for FR/CDR comparison\n')
    lines.insert(insert_idx + 1, '  window.__vhvlLastVL = vl;\n')
    with open('api/static/console.html', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f'OK — inserted at line {insert_idx}')
