import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image
from database import get_all_attendees  # Or however you fetch data

st.set_page_config(layout="wide")
st.title("🪪 Badge Generator")

# Layout settings
BADGES_PER_ROW = 3

def generate_qr_code(data):
    qr = qrcode.QRCode(box_size=2, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# Fetch all attendees
attendees = get_all_attendees()

# Show instructions
st.markdown("⬇️ **Copy and paste these into a Word or Docs template.** Each badge is roughly 2.3×3.4 in when printed 3 across a page.")

# Layout in rows
cols = st.columns(BADGES_PER_ROW)
for idx, attendee in enumerate(attendees):
    col = cols[idx % BADGES_PER_ROW]

    with col:
        st.markdown("---")
        st.markdown(f"**Name:** {attendee['name']}")
        st.markdown(f"**Email:** {attendee['email']}")
        st.markdown(f"**Badge #:** {attendee['badge_number']}")
        
        # QR code content can be just the badge number or full name
        qr_data = f"{attendee['badge_number']}"
        qr_img_bytes = generate_qr_code(qr_data)
        st.image(qr_img_bytes, width=80)  # Adjust to fit visually
        st.markdown("---")
