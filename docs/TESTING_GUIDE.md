# GraphRAG UI Testing Guide

## 🧪 How to Test All Features

### **Starting the Application**

```bash
cd /home/jmagar/code/graphrag
npm run dev:web

# Or directly:
cd apps/web
npm run dev
```

The app will be available at: **http://localhost:3001**

---

## ✅ Features to Test

### **1. Left Sidebar**

#### Header
- [ ] Click "Add Source" button → Should show alert
- [ ] Verify GraphRAG logo displays correctly
- [ ] Check lightning icon is visible

#### Spaces Section
- [ ] "Work" space should be highlighted (blue background)
- [ ] Hover over "Play" and "Dev" spaces → Background changes
- [ ] Icons display correctly for all spaces
- [ ] Source counts visible (247, 89, 156)

#### Tags Section
- [ ] All 8 tags display with different colors
- [ ] Hover over tags → Background color changes
- [ ] Tag sizes vary (some larger, some smaller)
- [ ] Colors: blue, emerald, purple, amber, cyan, rose, indigo, teal

#### Statistics
- [ ] Documents: 1,247
- [ ] Vectors: 45.2K
- [ ] Storage: 2.4 GB
- [ ] All stats aligned properly

#### Scrollbar
- [ ] Custom scrollbar appears when content exceeds height
- [ ] Scrollbar is zinc colored (#3f3f46)
- [ ] Hover changes color to lighter zinc

---

### **2. Chat Header**

#### Title Section
- [ ] "GraphRAG Configuration" displays
- [ ] Green dot indicator visible
- [ ] "3 sources" text shows

#### Tabs
- [ ] "Chat" tab is active (blue highlight)
- [ ] Click each tab → Active state changes
- [ ] Click active tab again → Dropdown appears
- [ ] Dropdown aligns with clicked tab
- [ ] Click outside dropdown → Closes

#### Tab Dropdowns Content
- **Chat**: New Chat, Recent Chats
- **Sources**: Add Source, Connect URL
- **Graph**: View Graph, Search Nodes
- **Pins**: Pinned Items, Favorites
- **Composer**: New Document, Templates, Rich Editor
- **Explore**: Discover, Deep Dive

#### Action Buttons
- [ ] Export button (download icon)
- [ ] Share button (gradient blue, share icon)
- [ ] Hover effects on both buttons

---

### **3. Messages**

#### AI Message (Mandalorian Avatar)
- [ ] Avatar displays Mandalorian helmet
  - Gray background
  - T-shaped visor
  - Side details
  - Chin piece
- [ ] Two paragraphs of text
- [ ] "Qdrant" is bold and blue
- [ ] Text fades in with delay
- [ ] Citation badge [1] "Getting Started"
- [ ] Citation has emerald gradient
- [ ] Hover over message → Timestamp appears (2:34 PM)

#### Message Actions
- [ ] Thumbs up button → Shows "2"
- [ ] Click thumbs up → Toggles blue background
- [ ] Copy button → Hover changes color
- [ ] Regenerate button → Hover changes color
- [ ] Timestamp hidden → Shows on group hover

#### User Message (Grogu Avatar)
- [ ] Avatar displays Grogu (Baby Yoda)
  - Green background
  - Round head
  - Big ears
  - Large eyes
- [ ] Message has blue gradient background
- [ ] White text
- [ ] Right-aligned
- [ ] Hover → Edit button appears
- [ ] Hover → Timestamp appears (2:35 PM)

---

### **4. Chat Input**

#### Textarea
- [ ] Placeholder text: "Ask me anything..."
- [ ] Type text → Textarea grows
- [ ] Max height: 200px, then scrolls
- [ ] Min height: 36px

#### Send Button
- [ ] Disabled when empty (gray)
- [ ] Enabled when text entered (blue gradient)
- [ ] Click → Sends message
- [ ] Hover → Shadow increases

#### Attach Button
- [ ] Paperclip icon
- [ ] Hover → Background changes
- [ ] Hover → Scales up slightly

#### AI Enhance Button
- [ ] Purple sparkle icon
- [ ] Hover → Background purple
- [ ] Hover → Scales up

---

### **5. Keyboard Shortcuts**

#### ⌘+K (Focus Input)
- [ ] Press `Cmd+K` (Mac) or `Ctrl+K` (Windows/Linux)
- [ ] Input field gets focus
- [ ] Footer hints change

#### ⌘+Enter (Send Message)
- [ ] Type message
- [ ] Press `Cmd+Enter` or `Ctrl+Enter`
- [ ] Message sends
- [ ] Input clears

---

### **6. Commands Dropdown (/ trigger)**

#### Activation
- [ ] Type `/` in input
- [ ] Dropdown appears above input
- [ ] Shows 7 commands

#### Commands List
1. [ ] `/config` - Configure settings (blue, gear icon)
2. [ ] `/commands` - View all commands (purple, terminal icon)
3. [ ] `/agents` - Manage AI agents (emerald, users icon)
4. [ ] `/search` - Search sources (cyan, search icon)
5. [ ] `/crawl` - Crawl a website (amber, globe icon)
6. [ ] `/query` - Custom query (rose, question icon)
7. [ ] `/model` - Switch AI model (indigo, lightbulb icon)

#### Navigation
- [ ] Arrow Down → Highlights next command
- [ ] Arrow Up → Highlights previous command
- [ ] Selected command has light gray background
- [ ] Enter → Inserts command into input
- [ ] Escape → Closes dropdown

#### Interaction
- [ ] Click command → Inserts into input
- [ ] Hover over command → Highlights it
- [ ] Dropdown closes after selection

---

### **7. Mentions Dropdown (@ trigger)**

#### Activation
- [ ] Type `@` in input
- [ ] Dropdown appears
- [ ] Shows 2 sources

#### Sources
1. [ ] Getting Started Guide - 247 chunks (emerald, document icon)
2. [ ] API Documentation - 189 chunks (blue, code icon)

#### Interaction
- [ ] Click source → Inserts into input as `@SourceName`
- [ ] Hover → Background changes

---

### **8. Input Footer**

#### When Not Focused
- [ ] Shows "Press ⌘ + K to focus"
- [ ] Keyboard shortcuts styled with border

#### When Focused
- [ ] Shows "Type @ to mention sources or / for commands"
- [ ] Shows "⌘ + Enter" shortcut
- [ ] All kbd elements styled consistently

---

### **9. Right Sidebar Workflows**

#### Workflow Cards
1. [ ] **Create** (blue)
2. [ ] **Report** (emerald)
3. [ ] **Mind Map** (purple)
4. [ ] **Graph** (cyan)
5. [ ] **Plan** (amber)
6. [ ] **PRD** (rose)
7. [ ] **Tasks** (indigo)

#### Hover Effects
- [ ] Hover → Border color changes to workflow color
- [ ] Hover → Background gets subtle color tint
- [ ] Hover → Icon background darkens
- [ ] Transition is smooth

#### Layout
- [ ] Cards stack vertically
- [ ] Equal spacing between cards
- [ ] Icons aligned left
- [ ] Text aligned properly

---

### **10. Dark Mode**

#### Toggle Dark Mode
```javascript
// Open browser console and run:
document.documentElement.classList.toggle('dark')
```

#### What to Check
- [ ] Background changes to zinc-950
- [ ] Text becomes lighter (zinc-50/100)
- [ ] Borders become zinc-800
- [ ] Hover states work correctly
- [ ] Shadows adjust for dark background
- [ ] All colors maintain contrast
- [ ] Gradient buttons still visible
- [ ] Citations readable
- [ ] Avatars display correctly

---

### **11. Animations**

#### Message Animations
- [ ] New messages slide up from below
- [ ] Text paragraphs fade in with stagger
- [ ] Animation duration: 0.3s for slide-up
- [ ] Animation duration: 0.5s for fade-in

#### Hover Animations
- [ ] Buttons scale on hover (1.05)
- [ ] Smooth transitions (150ms)
- [ ] Shadow grows on hover

---

### **12. Scrolling**

#### Left Sidebar
- [ ] Scroll when content exceeds height
- [ ] Custom scrollbar appears
- [ ] Smooth scrolling

#### Messages Container
- [ ] Scrollable area
- [ ] Bottom padding for input (128px / pb-32)
- [ ] Smooth scrolling

#### Right Sidebar
- [ ] Scrollable when needed
- [ ] Custom scrollbar

---

### **13. Responsive Behavior**

#### Sidebars
- [ ] Left sidebar: Fixed 288px (w-72)
- [ ] Right sidebar: Fixed 288px (w-72)
- [ ] Sidebars maintain width

#### Main Area
- [ ] Takes remaining space (flex-1)
- [ ] Content max-width: 3xl (768px)
- [ ] Centered in available space

---

### **14. Sending Messages**

#### Flow
1. [ ] Type message in input
2. [ ] Click send or press ⌘+Enter
3. [ ] Message appears as user message (right side, blue bubble)
4. [ ] Input clears
5. [ ] After 1 second, AI response appears
6. [ ] AI response has avatar and timestamp
7. [ ] Messages stack vertically

---

### **15. Edge Cases**

#### Empty Input
- [ ] Send button disabled
- [ ] Can't send with ⌘+Enter
- [ ] Clicking disabled button does nothing

#### Long Messages
- [ ] Textarea grows to 200px max
- [ ] Then scrolls internally
- [ ] Maintains readability

#### Long Text in Bubbles
- [ ] User messages wrap at 2xl max-width
- [ ] AI messages wrap with proper spacing
- [ ] No horizontal overflow

#### Click Outside
- [ ] Tab dropdown closes
- [ ] Command dropdown closes
- [ ] Mention dropdown closes

---

## 🐛 Known Issues

None currently! All features working as expected. ✅

---

## 🎯 Success Checklist

Run through this final checklist:

- [ ] All sidebar sections render correctly
- [ ] Tabs switch and show dropdowns
- [ ] Messages display with avatars
- [ ] Input system works (resize, send, shortcuts)
- [ ] Dropdowns appear and navigate correctly
- [ ] Keyboard shortcuts function
- [ ] Animations play smoothly
- [ ] Dark mode works
- [ ] Scrolling is smooth with custom scrollbars
- [ ] Workflow cards are interactive
- [ ] All hover states work
- [ ] No console errors
- [ ] Typography is consistent
- [ ] Colors match the mockup

---

## 📸 Screenshot Comparison

Compare your running app with the original `notebooklm-final.html`:

1. Open both in browser
2. Toggle dark mode in both
3. Compare:
   - Spacing and alignment
   - Colors and gradients
   - Font sizes
   - Icons
   - Hover states
   - Animations

They should be **identical**. ✅

---

## 🚀 Performance Testing

### Check Frame Rate
```javascript
// In browser console:
let frameCount = 0;
let lastTime = performance.now();
function countFrames() {
  frameCount++;
  const currentTime = performance.now();
  if (currentTime - lastTime >= 1000) {
    console.log(`FPS: ${frameCount}`);
    frameCount = 0;
    lastTime = currentTime;
  }
  requestAnimationFrame(countFrames);
}
countFrames();
```

**Expected**: ~60 FPS consistently

---

## ✅ All Tests Passed?

If yes, congratulations! The implementation is complete and working perfectly. 🎉

If you found any issues, please document them and we'll fix them immediately.
