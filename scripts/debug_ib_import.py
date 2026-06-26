import sys
print(sys.executable)
try:
    import ImmuneBuilder
    print("ImmuneBuilder imported:", ImmuneBuilder.__file__)
    print("Dir:", dir(ImmuneBuilder))
    from ImmuneBuilder import ABodyBuilder2
    print("ABodyBuilder2 imported")
except Exception as e:
    print("Error:", e)
