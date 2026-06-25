c = open(r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\therasik_index.html', encoding='utf-8').read
print('bispecific renamed:', '' in c)
print('team CU:', '' in c)
print('team CAS:', '' in c)
print('team THU:', '' in c)
print('mission+vision:', '' in c and '' in c)
print('therasik meaning:', 'Therapeutic' in c and 'Kinetics' in c)
print('standalone :', '#workflow"></a>' in c)
# check about section length
start = c.find('<section id="about"')
end = c.find('</section>', start) + 10
print(f'about section length: {end-start} chars')
