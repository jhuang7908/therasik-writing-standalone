import re

file_path = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Pitch_Deck.html"

with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

canvas_script = """
  <canvas id="tech-canvas" style="position:absolute; top:0; left:0; width:100%; height:100%; z-index:1; opacity:0.85; mix-blend-mode:screen; pointer-events:none;"></canvas>
  <script>
    (function(){
      const canvas = document.getElementById('tech-canvas');
      if(!canvas) return;
      const ctx = canvas.getContext('2d');
      let width, height;
      function resize() {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
      }
      window.addEventListener('resize', resize);
      resize();

      const particles = [];
      for(let i=0; i<60; i++) {
        particles.push({
          x: Math.random() * 2000, y: Math.random() * 1200,
          vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3,
          r: Math.random() * 2 + 0.5
        });
      }

      let time = 0;
      function draw() {
        if (!document.getElementById('tech-canvas')) return;
        ctx.clearRect(0, 0, width, height);
        time += 0.012;

        // 1. AI Molecular Network & Circuit Paths
        for(let i=0; i<particles.length; i++) {
          let p = particles[i];
          p.x += p.vx; p.y += p.vy;
          if(p.x < 0 || p.x > width) p.vx *= -1;
          if(p.y < 0 || p.y > height) p.vy *= -1;
          
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.r, 0, Math.PI*2);
          ctx.fillStyle = 'rgba(94, 234, 212, 0.4)';
          ctx.fill();

          for(let j=i+1; j<particles.length; j++) {
            let p2 = particles[j];
            let dist = Math.hypot(p.x - p2.x, p.y - p2.y);
            if(dist < 150) {
              ctx.beginPath();
              ctx.moveTo(p.x, p.y);
              // Draw 90-degree circuit-like pathways rather than organic lines
              if (Math.abs(p.x - p2.x) > Math.abs(p.y - p2.y)) {
                ctx.lineTo(p2.x, p.y); ctx.lineTo(p2.x, p2.y);
              } else {
                ctx.lineTo(p.x, p2.y); ctx.lineTo(p2.x, p2.y);
              }
              ctx.strokeStyle = `rgba(14, 165, 233, ${0.1 * (1 - dist/150)})`;
              ctx.lineWidth = 0.8;
              ctx.stroke();
            }
          }
        }

        // 2. DNA Double Helix (Left boundary)
        const centerX = Math.min(width * 0.12, 200);
        ctx.lineWidth = 1;
        for(let y = -50; y < height + 50; y += 18) {
          const offset = (y * 0.01) - time * 2;
          const x1 = centerX + Math.sin(offset) * 35;
          const x2 = centerX + Math.sin(offset + Math.PI) * 35;
          ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(x2, y);
          ctx.strokeStyle = 'rgba(94, 234, 212, 0.15)'; ctx.stroke();
          ctx.beginPath(); ctx.arc(x1, y, 2, 0, Math.PI*2); ctx.fillStyle = 'rgba(14, 165, 233, 0.4)'; ctx.fill();
          ctx.beginPath(); ctx.arc(x2, y, 2, 0, Math.PI*2); ctx.fillStyle = 'rgba(94, 234, 212, 0.4)'; ctx.fill();
        }
        
        // 3. Abstract Antibodies (Floating in logic space)
        const drawAb = (bx, by, scale, rot) => {
          ctx.save();
          ctx.translate(bx, by);
          ctx.rotate(rot + Math.sin(time)*0.1);
          ctx.scale(scale, scale);
          ctx.beginPath();
          ctx.moveTo(0, 45); ctx.lineTo(0, 0); // Trunk
          ctx.lineTo(-30, -40); ctx.moveTo(0, 0); ctx.lineTo(30, -40); // Arms
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
          ctx.lineWidth = 6; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
          ctx.stroke();
          ctx.beginPath(); ctx.moveTo(-15, -15); ctx.lineTo(15, -15); // Disulfide bond
          ctx.strokeStyle = 'rgba(94, 234, 212, 0.2)'; ctx.lineWidth = 2; ctx.stroke();
          ctx.restore();
        };
        
        drawAb(width * 0.88, height * 0.4 + Math.sin(time*1.5)*30, 1.4, 0.2);
        drawAb(width * 0.72, height * 0.8 + Math.cos(time)*20, 0.9, -0.4);

        requestAnimationFrame(draw);
      }
      draw();
    })();
  </script>
"""

if '<canvas id="tech-canvas"' not in html:
    idx = html.find('id="s1"')
    if idx != -1:
        end_tag = html.find('>', idx)
        if end_tag != -1:
            html = html[:end_tag+1] + "\n" + canvas_script + html[end_tag+1:]

# Elevate z-index for inner content so text stays crisp above canvas
html = html.replace('.slide-inner{', '.slide-inner{z-index:10;position:relative;')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Canvas background successfully injected!")
