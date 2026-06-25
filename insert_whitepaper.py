import os

file_path = 'therasik-web-source/Therasik_Antibody_Page.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read

insertion_point = '<p class="input-note">： PDB（Ab-Ag、- VHH-）。（ CDR-H3）。</p>'

new_html = """
<div style="margin-top:2.5rem;background:#fff;border-radius:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.05);border:1px solid #f3f4f6;overflow:hidden;">
  <div style="padding:2rem 2.5rem;">
    <div style="display:inline-flex;align-items:center;gap:0.5rem;padding:0.25rem 0.75rem;border-radius:9999px;background:#eef2ff;color:#4338ca;font-size:0.875rem;font-weight:600;margin-bottom:1.5rem;">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 2v7.31"/><path d="M14 9.3V1.99"/><path d="M8.5 2h7"/><path d="M14 9.3a6.5 6.5 0 1 1-4 0"/><line x1="8.5" y1="14" x2="15.5" y2="14"/></svg>
      
    </div>
    <h3 style="font-size:1.5rem;font-weight:700;color:#111827;margin-bottom:1rem;margin-top:0;">“”：InSynBio </h3>
    <p style="color:#4b5563;margin-bottom:2rem;line-height:1.75;">
       800+ ，“（ Rosetta/EvoEF）”<strong></strong>。 Top-K 。，Therasik  <strong>AI-MD  (Multi-Scale Cascade Engine)</strong>。
    </p>

    <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));gap:2.5rem;align-items:center;">
      <!-- Funnel Visualization -->
      <div>
        <h4 style="font-size:0.875rem;font-weight:600;color:#111827;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:1rem;">5  (Sequential Gating)</h4>
        
        <div style="display:flex;flex-direction:column;gap:0.75rem;">
          <!-- Stage 1 -->
          <div style="position:relative;display:flex;align-items:center;padding:1rem;background:#f9fafb;border-radius:0.5rem;border:1px solid #f3f4f6;">
            <div style="width:2.5rem;height:2.5rem;flex-shrink:0;background:#dbeafe;color:#2563eb;border-radius:9999px;display:flex;align-items:center;justify-content:center;font-weight:700;margin-right:1rem;">1</div>
            <div>
              <div style="font-weight:600;color:#111827;margin-bottom:0.25rem;">AI </div>
              <div style="font-size:0.875rem;color:#6b7280;">，/</div>
            </div>
            <div style="position:absolute;right:1rem;font-size:0.875rem;font-weight:700;color:#9ca3af;">10,000+</div>
          </div>
          
          <!-- Stage 2 -->
          <div style="position:relative;display:flex;align-items:center;padding:1rem;background:#f9fafb;border-radius:0.5rem;border:1px solid #f3f4f6;margin-left:1rem;">
            <div style="width:2.5rem;height:2.5rem;flex-shrink:0;background:#e0e7ff;color:#4f46e5;border-radius:9999px;display:flex;align-items:center;justify-content:center;font-weight:700;margin-right:1rem;">2</div>
            <div>
              <div style="font-weight:600;color:#111827;margin-bottom:0.25rem;"></div>
              <div style="font-size:0.875rem;color:#6b7280;"> Non-binder</div>
            </div>
            <div style="position:absolute;right:1rem;font-size:0.875rem;font-weight:700;color:#9ca3af;">~3,000</div>
          </div>

          <!-- Stage 3 -->
          <div style="position:relative;display:flex;align-items:center;padding:1rem;background:#f9fafb;border-radius:0.5rem;border:1px solid #f3f4f6;margin-left:2rem;">
            <div style="width:2.5rem;height:2.5rem;flex-shrink:0;background:#f3e8ff;color:#7e22ce;border-radius:9999px;display:flex;align-items:center;justify-content:center;font-weight:700;margin-right:1rem;">3</div>
            <div>
              <div style="font-weight:600;color:#111827;margin-bottom:0.25rem;">3D AI </div>
              <div style="font-size:0.875rem;color:#6b7280;"> 3D ，</div>
            </div>
            <div style="position:absolute;right:1rem;font-size:0.875rem;font-weight:700;color:#9ca3af;">~500</div>
          </div>

          <!-- Stage 4 -->
          <div style="position:relative;display:flex;align-items:center;padding:1rem;background:#f9fafb;border-radius:0.5rem;border:1px solid #f3f4f6;margin-left:3rem;">
            <div style="width:2.5rem;height:2.5rem;flex-shrink:0;background:#ccfbf1;color:#0d9488;border-radius:9999px;display:flex;align-items:center;justify-content:center;font-weight:700;margin-right:1rem;">4</div>
            <div>
              <div style="font-weight:600;color:#111827;margin-bottom:0.25rem;"></div>
              <div style="font-size:0.875rem;color:#6b7280;">， pI </div>
            </div>
            <div style="position:absolute;right:1rem;font-size:0.875rem;font-weight:700;color:#9ca3af;">~150</div>
          </div>

          <!-- Stage 5 -->
          <div style="position:relative;display:flex;align-items:center;padding:1rem;background:#ecfdf5;border-radius:0.5rem;border:1px solid #a7f3d0;margin-left:4rem;box-shadow:0 1px 2px rgba(0,0,0,0.05);">
            <div style="width:2.5rem;height:2.5rem;flex-shrink:0;background:#10b981;color:#fff;border-radius:9999px;display:flex;align-items:center;justify-content:center;font-weight:700;margin-right:1rem;">5</div>
            <div>
              <div style="font-weight:600;color:#065f46;margin-bottom:0.25rem;"> MD </div>
              <div style="font-size:0.875rem;color:#047857;">，</div>
            </div>
            <div style="position:absolute;right:1rem;font-size:0.875rem;font-weight:700;color:#059669;">Top 10</div>
          </div>
        </div>
      </div>

      <!-- Chart / Stats -->
      <div style="background:#f9fafb;padding:1.5rem;border-radius:0.75rem;border:1px solid #e5e7eb;">
        <h4 style="font-size:0.875rem;font-weight:600;color:#111827;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:1.5rem;">：</h4>
        <div style="display:flex;flex-direction:column;gap:1.25rem;">
          <div>
            <div style="display:flex;justify-content:space-between;font-size:0.875rem;margin-bottom:0.25rem;"><span style="color:#4b5563;"></span><span style="font-weight:700;color:#111827;">74.5%</span></div>
            <div style="width:100%;background:#e5e7eb;border-radius:9999px;height:0.5rem;"><div style="background:#9ca3af;height:0.5rem;border-radius:9999px;width:74.5%;"></div></div>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;font-size:0.875rem;margin-bottom:0.25rem;"><span style="color:#4b5563;"> AI </span><span style="font-weight:700;color:#111827;">77.8%</span></div>
            <div style="width:100%;background:#e5e7eb;border-radius:9999px;height:0.5rem;"><div style="background:#3b82f6;height:0.5rem;border-radius:9999px;width:77.8%;"></div></div>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;font-size:0.875rem;margin-bottom:0.25rem;"><span style="color:#4b5563;"></span><span style="font-weight:700;color:#111827;">78.5%</span></div>
            <div style="width:100%;background:#e5e7eb;border-radius:9999px;height:0.5rem;"><div style="background:#6366f1;height:0.5rem;border-radius:9999px;width:78.5%;"></div></div>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;font-size:0.875rem;margin-bottom:0.25rem;"><span style="color:#4b5563;"> + MD </span><span style="font-weight:700;color:#059669;">82.4%+</span></div>
            <div style="width:100%;background:#e5e7eb;border-radius:9999px;height:0.5rem;"><div style="background:#10b981;height:0.5rem;border-radius:9999px;width:82.4%;"></div></div>
          </div>
        </div>
        <div style="margin-top:1.5rem;padding-top:1.5rem;border-top:1px solid #e5e7eb;font-size:0.875rem;color:#6b7280;line-height:1.5;">
          <strong>：</strong>，。、、，。
        </div>
      </div>
    </div>
  </div>
</div>
"""

if insertion_point in content and "“”" not in content:
    content = content.replace(insertion_point, insertion_point + '\n' + new_html)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully inserted the whitepaper section.")
else:
    print("Insertion point not found or already inserted.")
