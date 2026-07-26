import os
import random
import datetime
import google.generativeai as genai

# Setup Gemini API
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY secret is not set in GitHub Repository Secrets!")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# Local SEO Topics for Cape Town Electrician
topics = [
    "How to Prepare Your Home Electrical DB Board for Load Shedding in Cape Town",
    "What Is a COC Certificate and Why You Need One When Selling Property in Western Cape",
    "Common Electrical Faults in Cape Town Homes and How to Spot Them",
    "Upgrading Your Home Distribution Board DB Safety Tips and Standards",
    "Solar PV and Inverter Installations What Every Cape Town Homeowner Should Know"
]

selected_topic = random.choice(topics)
date_str = datetime.datetime.now().strftime("%Y-%m-%d")
slug = selected_topic.lower().replace(" ", "-")

prompt = f"""
Write an engaging, SEO-optimized blog post in clean HTML format (only content inside <body> tag, no <html> or <body> tags) about: "{selected_topic}".

Requirements:
- Target Audience: Homeowners and business owners in Cape Town Metro.
- Mention: Adie's Electrical Solutions (licensed Cape Town electrician).
- Include headings (<h2>, <h3>), practical electrical safety tips, and a call to action inviting readers to WhatsApp +27 84 729 9088 or email info@adieselectrical.co.za for a quote.
- Maintain professional, helpful tone.
"""

response = model.generate_content(prompt)
blog_content = response.text.replace("```html", "").replace("```", "")

# Wrap in simple HTML template
full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{selected_topic} | Adie's Electrical Solutions</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; }}
        h1, h2, h3 {{ color: #111; }}
        .cta {{ background: #f4f4f4; padding: 20px; border-left: 4px solid #0070f3; margin-top: 30px; }}
        a {{ color: #0070f3; text-decoration: none; }}
    </style>
</head>
<body>
    <p><a href="../index.html">&larr; Back to Home</a></p>
    <h1>{selected_topic}</h1>
    <p><em>Published on {date_str} by Adie's Electrical Solutions</em></p>
    <hr>
    {blog_content}
    <div class="cta">
        <h3>Need Professional Electrical Work in Cape Town?</h3>
        <p>Contact Adie's Electrical Solutions for COC Inspections, Fault Finding, and Solar Setup.</p>
        <p>📞 <strong>Phone/WhatsApp:</strong> <a href="https://wa.me/27847299088">084 729 9088</a> | ✉️ <strong>Email:</strong> info@adieselectrical.co.za</p>
    </div>
</body>
</html>
"""

# Save to blog folder
os.makedirs("blog", exist_ok=True)
filename = f"blog/{slug}.html"
with open(filename, "w", encoding="utf-8") as f:
    f.write(full_html)

print(f"Successfully generated: {filename}")
