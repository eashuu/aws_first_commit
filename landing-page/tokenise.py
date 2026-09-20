import re
import os

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    replacements = [
        # Z-index
        (r'z-index:\s*2;', 'z-index: var(--z-raised);'),
        (r'z-index:\s*1;', 'z-index: var(--z-base);'),
        (r'z-index:\s*0;', 'z-index: var(--z-ground);'),
        
        # Radii
        (r'border-radius:\s*99px;', 'border-radius: var(--radius-full);'),
        (r'border-radius:\s*50%;', 'border-radius: var(--radius-full);'),
        (r'border-radius:\s*1px;', 'border-radius: var(--radius-2xs);'),
        (r'border-radius:\s*2px;', 'border-radius: var(--radius-xs);'),
        (r'border-radius:\s*3px;', 'border-radius: var(--radius-xs);'),
        
        # Colors (Rose Alphas)
        (r'rgba\(222,\s*161,\s*147,\s*0\.025\)', 'var(--rose-a02)'), # approx
        (r'rgba\(222,\s*161,\s*147,\s*0\.07\)', 'var(--rose-a07)'),
        (r'rgba\(222,\s*161,\s*147,\s*0\.08\)', 'var(--rose-a08)'),
        (r'rgba\(222,\s*161,\s*147,\s*0\.12\)', 'var(--rose-a12)'),
        (r'rgba\(222,\s*161,\s*147,\s*0\.15\)', 'var(--rose-a15)'),
        (r'rgba\(222,\s*161,\s*147,\s*0\.25\)', 'var(--rose-a25)'),
        (r'rgba\(222,\s*161,\s*147,\s*0\.3\)', 'var(--rose-a30)'),
        (r'rgba\(222,\s*161,\s*147,\s*0\.35\)', 'var(--rose-a35)'),
        (r'rgba\(222,\s*161,\s*147,\s*0\.4\)', 'var(--rose-a40)'),
        (r'rgba\(222,\s*161,\s*147,\s*0\.7\)', 'var(--rose-a70)'),
        (r'rgba\(222,\s*161,\s*147,\s*0\.8\)', 'var(--rose-a80)'),
        
        # Colors (White/Black Alphas)
        (r'rgba\(255,\s*255,\s*255,\s*0\.04\)', 'var(--white-a04)'),
        (r'rgba\(255,\s*255,\s*255,\s*0\.05\)', 'var(--white-a05)'),
        (r'rgba\(255,\s*255,\s*255,\s*0\.08\)', 'var(--white-a08)'),
        (r'rgba\(255,\s*255,\s*255,\s*0\.12\)', 'var(--white-a12)'),
        (r'rgba\(255,\s*255,\s*255,\s*0\.20\)', 'var(--white-a20)'),
        (r'rgba\(255,\s*255,\s*255,\s*0\.2\)', 'var(--white-a20)'),
        (r'rgba\(0,\s*0,\s*0,\s*0\.3\)', 'var(--black-a30)'),
        (r'rgba\(0,\s*0,\s*0,\s*0\.45\)', 'var(--black-a45)'),
        
        # Status Colors
        (r'rgba\(107,\s*123,\s*101,\s*0\.12\)', 'var(--status-success-bg)'),
        (r'rgba\(107,\s*123,\s*101,\s*0\.25\)', 'var(--status-success-border)'),
        (r'rgba\(142,\s*90,\s*90,\s*0\.12\)', 'var(--status-danger-bg)'),
        (r'rgba\(142,\s*90,\s*90,\s*0\.25\)', 'var(--status-danger-border)'),
        (r'rgba\(142,\s*90,\s*90,\s*0\.4\)', 'var(--status-danger-strong)'),
        
        # Rogue Green
        (r'rgba\(100,\s*200,\s*130,\s*0\.6\)', 'var(--status-success)'),
        (r'rgba\(100,\s*200,\s*130,\s*0\.9\)', 'var(--status-success)'),
        (r'rgba\(100,\s*200,\s*130,\s*0\.7\)', 'var(--status-success)'),
        
        # Syntax Blue
        (r'#8CA9C5', 'var(--syntax-string)'),
        
        # Font Sizes (Mapping to tokens)
        (r'font-size:\s*0\.6rem;', 'font-size: var(--font-size-2xs);'),
        (r'font-size:\s*0\.62rem;', 'font-size: var(--font-size-xs);'),
        (r'font-size:\s*0\.64rem;', 'font-size: var(--font-size-xs);'),
        (r'font-size:\s*0\.65rem;', 'font-size: var(--font-size-xs);'),
        (r'font-size:\s*0\.66rem;', 'font-size: var(--font-size-xs);'),
        (r'font-size:\s*0\.68rem;', 'font-size: var(--font-size-xs);'),
        (r'font-size:\s*0\.7rem;', 'font-size: var(--font-size-xs);'),
        (r'font-size:\s*0\.72rem;', 'font-size: var(--font-size-xs);'),
        (r'font-size:\s*0\.75rem;', 'font-size: var(--font-size-xs);'),
        (r'font-size:\s*0\.82rem;', 'font-size: var(--font-size-sm);'),
        (r'font-size:\s*0\.85rem;', 'font-size: var(--font-size-sm);'),
        (r'font-size:\s*0\.9rem;', 'font-size: var(--font-size-base);'),
        (r'font-size:\s*1\.1rem;', 'font-size: var(--font-size-md);'),
    ]

    for old, new in replacements:
        content = re.sub(old, new, content)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

replace_in_file('e:/Drizzle/VS/Naka/landing-page/src/components/Section2/Section2.css')
replace_in_file('e:/Drizzle/VS/Naka/landing-page/src/components/Section3/Section3.css')
replace_in_file('e:/Drizzle/VS/Naka/landing-page/src/components/Section3/Section3.tsx')
