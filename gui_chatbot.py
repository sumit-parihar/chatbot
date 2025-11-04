# gui_chatbot.py
import tkinter as tk
from tkinter import ttk, Menu
import tkinter.font as tkfont
from PIL import Image, ImageTk
import json, random, os
from datetime import datetime
import webbrowser
import re

current_context = None


# ---------- load KB ----------
with open("knowledge_base.json", "r", encoding="utf-8") as f:
    kb = json.load(f)

# ---------- logging ----------
def log_chat(sender, message):
    os.makedirs("logs", exist_ok=True)
    with open("logs/chat_log.txt", "a", encoding="utf-8") as log:
        ts = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log.write(f"{ts} {sender}: {message}\n")

# ---------- matching ----------
def find_match(user_text):
    user_text = user_text.lower()
    for intent, data in kb.items():
        for kw in data.get("keywords", []):
            if kw in user_text:
                return random.choice(data["responses"]), False
    if "default" in kb:
        return random.choice(kb["default"]["responses"]), True
    return "I'm sorry, I didn’t quite get that.", True

# ---------- UI setup ----------
root = tk.Tk()
root.title("Chat with CSE Assistant")
root.geometry("480x640")
root.resizable(False, False)
root.config(bg="#E8F0FE")

# fonts
EMOJI_FONT = ("Segoe UI Emoji", 11)   # colored emoji on Windows if available
TEXT_FONT = ("Segoe UI", 10)
FONT_OBJ = tkfont.Font(family=EMOJI_FONT[0], size=EMOJI_FONT[1])

# ---------- header ----------
header = tk.Frame(root, bg="#1E88E5", height=70)
header.pack(fill="x")

profile_label = tk.Label(header, text="💬 Chat with CSE Assistant", font=("Segoe UI Emoji", 13, "bold"),
                         bg="#1E88E5", fg="white")
profile_label.pack(side="left", padx=15, pady=20)

# options (3-dot) -> menu with Exit
def open_options(event=None):
    menu = Menu(root, tearoff=0)
    menu.add_command(label="Exit", command=root.destroy)
    menu.tk_popup(root.winfo_pointerx(), root.winfo_pointery())

options_btn = tk.Label(header, text="⋮", bg="#1E88E5", fg="white", font=("Segoe UI", 16))
options_btn.pack(side="right", padx=12, pady=12)
options_btn.bind("<Button-1>", open_options)

status_label = tk.Label(header, text="We are online!", bg="#1E88E5", fg="white", font=("Segoe UI", 9))
status_label.place(x=15, y=46)

# ---------- chat area (canvas + scroll) ----------
chat_frame = tk.Frame(root, bg="#E8F0FE")
chat_frame.pack(padx=10, pady=8, fill="both", expand=True)

canvas = tk.Canvas(chat_frame, bg="#E8F0FE", highlightthickness=0)
vsb = ttk.Scrollbar(chat_frame, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas, bg="#E8F0FE")

# place the scrollable_frame inside canvas
scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0,0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=vsb.set)

canvas.pack(side="left", fill="both", expand=True)
vsb.pack(side="right", fill="y")

# enable mouse wheel scrolling
def _on_mousewheel(event):
    # Windows uses event.delta; positive scroll up
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
canvas.bind_all("<MouseWheel>", _on_mousewheel)

# ---------- helper: draw rounded rect on a canvas ----------
def _rounded_rect(cnv, x1, y1, x2, y2, radius=10, **kwargs):
    """Draw a rounded rectangle on canvas 'cnv' and return the object ids as a group."""
    # corners: arcs
    r = radius
    # rectangles/ovals to compose rounded rect
    items = []
    items.append(cnv.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, style="pieslice", **kwargs))
    items.append(cnv.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, style="pieslice", **kwargs))
    items.append(cnv.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, style="pieslice", **kwargs))
    items.append(cnv.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, style="pieslice", **kwargs))
    # center rectangles
    items.append(cnv.create_rectangle(x1+r, y1, x2-r, y2, **kwargs))
    items.append(cnv.create_rectangle(x1, y1+r, x2, y2-r, **kwargs))
    return items

# ---------- create bubble (rounded) ----------
def create_bubble(parent, text, who="bot", max_width_px=320, pad_x=12, pad_y=8):
    """
    Creates a Canvas widget with rounded background and text.
    Adds clickable links for emails and URLs.
    """
    # detect URLs and emails using regex
    url_pattern = r"(https?://[^\s]+|www\.[^\s]+)"
    email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"

    # wrap text into lines based on width
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        w_px = FONT_OBJ.measure(test)
        if w_px > max_width_px:
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)

    # measure sizes
    line_height = FONT_OBJ.metrics("linespace")
    text_height = line_height * len(lines)
    text_width = max((FONT_OBJ.measure(line) for line in lines), default=0)

    bubble_width = text_width + pad_x*2
    bubble_height = text_height + pad_y*2
    radius = 12

    # build canvas sized to bubble
    cnv = tk.Canvas(parent, width=bubble_width+4, height=bubble_height+4,
                    bg=parent["bg"], highlightthickness=0)

    # choose colors
    if who == "user":
        bg_color = "#D2E3FC"  # light blue user bubble
        text_color = "#000000"
    else:
        bg_color = "#FFFFFF"  # white bot bubble
        text_color = "#000000"

    # draw rounded background
    _rounded_rect(cnv, 2, 2, 2 + bubble_width, 2 + bubble_height,
                  radius=radius, fill=bg_color, outline=bg_color)

    # write text and create links
    y = pad_y + 2
    for line in lines:
        x = pad_x + 2
        for token in line.split(" "):
            token_text = token + " "
            # check if token is URL
            if re.match(url_pattern, token):
                link = cnv.create_text(x, y, anchor="nw", text=token_text,
                                       font=("Segoe UI", 10, "underline"),
                                       fill="#1E88E5", activefill="#0D47A1")
                cnv.tag_bind(link, "<Button-1>", lambda e, url=token: webbrowser.open(url if url.startswith("http") else "http://" + url))
            # check if token is email
            elif re.match(email_pattern, token):
                link = cnv.create_text(x, y, anchor="nw", text=token_text,
                                       font=("Segoe UI", 10, "underline"),
                                       fill="#1E88E5", activefill="#0D47A1")
                cnv.tag_bind(link, "<Button-1>", lambda e, addr=token: webbrowser.open(f"mailto:{addr}"))
            else:
                cnv.create_text(x, y, anchor="nw", text=token_text, font=EMOJI_FONT, fill=text_color)
            x += FONT_OBJ.measure(token_text)
        y += line_height

    cnv.config(width=min(bubble_width+4, 400), height=bubble_height+6)
    return cnv

# ---------- add message to UI ----------
def add_message(who, message):
    # container frame for bubble (so we can align left or right)
    container = tk.Frame(scrollable_frame, bg=scrollable_frame["bg"])
    container.pack(fill="x", pady=4, padx=6)

    bubble = create_bubble(container, message, who=who)

    # align: bot left, user right (extreme)
    if who == "user":
        bubble.pack(side="right", anchor="e", padx=(40,4))
    else:
        bubble.pack(side="left", anchor="w", padx=(4,40))

    # ensure widgets are updated so option_frame can be placed after this container
    root.update_idletasks()

    # If options are currently present (built), re-pack option_frame so it sits AFTER this new message
    # This ensures options are always directly below the last message.
    if option_frame.winfo_children():
        try:
            option_frame.pack_forget()
        except:
            pass
        option_frame.pack(fill="x", anchor="w", padx=10, pady=6)

    # Scroll to bottom to show the new message + options
    canvas.yview_moveto(1.0)

    log_chat(who, message)

# ---------- options buttons (multi-row grid) ----------
option_frame = tk.Frame(scrollable_frame, bg=scrollable_frame["bg"])

def show_options(context=None):
    global current_context
    current_context = context

    # ensure option_frame is cleared before adding buttons
    for widget in option_frame.winfo_children():
        widget.destroy()

    # Choose options set (main or submenu)
    if context is None:
        options = ["About Dept", "HOD", "Labs", "Contact", "Courses", "Exam Schedule", "Faculty", "Admission"]
    elif context == "Courses":
        options = ["OS", "DBMS", "DSA", "Machine Learning", "Cloud Computing", "⬅ Back"]
    elif context == "About Dept":
        options = ["Vision", "Mission", "Facilities", "Achievements", "⬅ Back"]
    elif context == "Labs":
        options = ["Software Lab", "Hardware Lab", "Research Lab", "⬅ Back"]
    else:
        options = ["⬅ Back"]

    # layout buttons in grid with wrap (3 columns by default)
    cols = 3
    for idx, text in enumerate(options):
        r = idx // cols
        c = idx % cols
        btn = tk.Button(
            option_frame,
            text=text,
            font=("Segoe UI", 9, "bold"),
            bg="#E3F2FD",
            fg="#0D47A1",
            relief="flat",
            padx=8,
            pady=6,
            cursor="hand2",
            command=lambda t=text: option_selected(t)
        )
        btn.grid(row=r, column=c, padx=6, pady=6, sticky="ew")

    # evenly expand columns so they look neat
    for c in range(cols):
        option_frame.grid_columnconfigure(c, weight=1)

    # pack the frame into the scrollable_frame (so it appears in message flow)
    # if it's already packed, pack_forget then pack again to move it to the bottom-most place
    try:
        option_frame.pack_forget()
    except:
        pass
    option_frame.pack(fill="x", anchor="w", padx=10, pady=6)

    # update layout and scroll to bottom to bring options into view
    root.update_idletasks()
    canvas.yview_moveto(1.0)

def clear_options():
    for widget in option_frame.winfo_children():
        widget.destroy()
    # don't destroy frame itself; just forget it from view
    try:
        option_frame.pack_forget()
    except:
        pass

def option_selected(option):
    global current_context
    clear_options()

    if option == "⬅ Back":
        show_options()  # Go back to main menu
        return

    # Navigate into sub-context
    if option == "Courses":
        show_options("Courses")
        return
    elif option == "About Dept":
        show_options("About Dept")
        return
    elif option == "Labs":
        show_options("Labs")
        return

    # Otherwise, treat as normal user message
    user_entry.delete(0, "end")
    user_entry.insert(0, option)
    send_message()


# ---------- bottom input bar ----------
bottom_frame = tk.Frame(root, bg="#FFFFFF", height=60)
bottom_frame.pack(fill="x", side="bottom")

user_entry = tk.Entry(bottom_frame, font=EMOJI_FONT, bg="#FFFFFF", relief="flat")
user_entry.pack(side="left", padx=(14,6), pady=12, fill="x", expand=True)
user_entry.bind("<Return>", lambda e: send_message())

# ---------- send logic ----------
def send_message():
    txt = user_entry.get().strip()
    if not txt:
        return
    clear_options()
    add_message("user", txt)
    user_entry.delete(0, "end")
    bot_resp, is_default = find_match(txt)
    # small simulated typing delay
    root.after(420, lambda: add_message("bot", bot_resp))
    if is_default:
        root.after(760, show_options)

# send button with resized icon (fallback to arrow)
def _make_send_button(parent):
    try:
        img = Image.open("assets/send_icon.png")
        img = img.resize((26, 26), Image.LANCZOS)
        img_tk = ImageTk.PhotoImage(img)
        
        # Create button with transparent-style background
        btn = tk.Button(
            parent,
            image=img_tk,
            bg="#FFFFFF",      # same as bottom bar background
            activebackground="#FFFFFF",
            bd=0,              # removes border
            highlightthickness=0,  # removes focus outline
            relief="flat",
            cursor="hand2",
            command=send_message
        )
        btn.image = img_tk  # keep a reference to avoid GC

        # Optional: make it appear circular if image background isn't transparent
        btn.config(padx=4, pady=4)
        btn.bind("<Enter>", lambda e: btn.config(bg="#E3F2FD"))  # hover effect
        btn.bind("<Leave>", lambda e: btn.config(bg="#FFFFFF"))

    except Exception:
        # fallback to emoji arrow if image missing
        btn = tk.Button(
            parent,
            text="➤",
            bg="#1E88E5",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            command=send_message
        )
    return btn


send_btn = _make_send_button(bottom_frame)
send_btn.pack(side="right", padx=12, pady=10)

# ---------- initial greeting ----------
greeting = "👋 Hi there! I’m your CSE Assistant. Choose a topic below or type a question."
add_message("bot", greeting)
show_options()

# ---------- ensure focus ----------
user_entry.focus_set()

root.mainloop()
