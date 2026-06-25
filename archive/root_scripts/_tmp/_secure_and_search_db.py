import re

path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read

# 1. Update Security Script (Anti-copy, Anti-crawling)
old_security = r'''// Security: Anti-copy, Anti-right-click, Anti-print
\(function\(\) \{
  document\.addEventListener\('contextmenu', e => e\.preventDefault\(\)\);
  document\.addEventListener\('selectstart', e => e\.preventDefault\(\)\);
  document\.addEventListener\('copy', e => e\.preventDefault\(\)\);
  document\.addEventListener\('keydown', e => \{
    if \(\(e\.ctrlKey \|\| e\.metaKey\) && \(e\.key === 'c' \|\| e\.key === 'p' \|\| e\.key === 's' \|\| e\.key === 'u'\)\) \{
      e\.preventDefault\(\);
    \}
  \}\);
\}\)\(\);'''

new_security = r'''// Security: Anti-copy, Anti-crawling, Anti-debugging
(function {
  // Disable right-click, text selection, and copy
  document.addEventListener('contextmenu', e => e.preventDefault);
  document.addEventListener('selectstart', e => e.preventDefault);
  document.addEventListener('copy', e => e.preventDefault);
  
  // Block common devtool shortcuts
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'p' || e.key === 's' || e.key === 'u' || e.key === 'i' || e.key === 'j')) {
      e.preventDefault;
    }
    if (e.key === 'F12') e.preventDefault;
  });

  // Anti-debugging: detect DevTools opening
  setInterval( => {
    const start = Date.now;
    debugger;
    if (Date.now - start > 100) {
      document.body.innerHTML = '<div style="padding:50px;text-align:center;font-family:sans-serif;"><h2>Security Alert</h2><p>Unauthorized access detected. This database is protected.</p></div>';
    }
  }, 1000);

  // Anti-crawling: detect rapid requests or headless browsers
  if (navigator.webdriver) {
    document.body.innerHTML = '<h1>Access Denied</h1>';
  }
});'''

content = re.sub(old_security, new_security, content, flags=re.DOTALL)

# 2. Add Global Search Input
search_bar_html = '''    <div class="search-container" style="margin-bottom: 20px; position: sticky; top: 0; z-index: 100; background: white; padding: 10px; border-bottom: 2px solid var(--primary);">
      <input type="text" id="globalSearch" placeholder="🔍  (, , , )..." style="width: 100%; padding: 12px; border: 2px solid var(--primary); border-radius: 8px; font-size: 16px;">
    </div>'''

# Insert after the tabs navigation
tabs_nav_end = '</div>\n\n  <!-- ── Tab Panels ── -->'
if tabs_nav_end in content:
    content = content.replace(tabs_nav_end, tabs_nav_end + '\n' + search_bar_html)

# 3. Add Global Search Logic
global_search_js = '''
/* ── Global Search Logic ── */
document.getElementById('globalSearch').addEventListener('input', function(e) {
  var q = e.target.value.toLowerCase;
  if (!q) {
    // If empty, just show active tab as normal
    filterActiveTab;
    return;
  }
  
  // Search across ALL tabs
  var allCards = document.querySelectorAll('.card');
  var n = 0;
  allCards.forEach(function(card) {
    var text = (card.innerText + ' ' + (card.dataset.search || '')).toLowerCase;
    var show = text.includes(q);
    card.classList.toggle('hidden', !show);
    if (show) n++;
  });
  
  // Show all panels that have results
  document.querySelectorAll('.tab-panel').forEach(function(panel) {
    var visibleCards = panel.querySelectorAll('.card:not(.hidden)');
    panel.style.display = visibleCards.length > 0 ? 'block' : 'none';
  });
});

// Update filterActiveTab to handle global search state
var originalFilterActiveTab = filterActiveTab;
filterActiveTab = function {
  var gq = document.getElementById('globalSearch').value;
  if (gq) return; // Don't override global search results
  
  // Reset display styles for panels
  document.querySelectorAll('.tab-panel').forEach(function(panel) {
    panel.style.display = '';
  });
  originalFilterActiveTab;
};
'''

# Append to the end of script
content = content.replace('</script>', global_search_js + '\n</script>')

# 4. Hide "Clinical ADC Programs" tab for public users
# We will hide the tab button and the panel
content = content.replace('<button class="tab-btn active" data-tab="programs">Clinical ADC Programs</button>', 
                          '<!-- <button class="tab-btn active" data-tab="programs">Clinical ADC Programs</button> -->')
content = content.replace('id="panel-programs"', 'id="panel-programs" style="display:none;"')

# Set another tab as active by default (e.g., antigens)
content = content.replace('<button class="tab-btn" data-tab="antigens">Target Antigens</button>', 
                          '<button class="tab-btn active" data-tab="antigens">Target Antigens</button>')
content = content.replace('id="panel-antigens"', 'id="panel-antigens" class="active"')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Security and search enhancements applied.")
