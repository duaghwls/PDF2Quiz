import streamlit as st
import fitz  # PyMuPDF
import re

st.set_page_config(page_title="PDF2Quiz Interactive App", layout="wide")

def clean_text(text):
    # Replace newlines with spaces for natural sentences, unless it's a double newline
    # Also strip extra whitespaces
    return re.sub(r'(?<!\n)\n(?!\n)', ' ', text).strip()

def parse_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    
    # We need to find the exact start point: ^Q1$
    # We'll split the text by lines to find the marker.
    lines = full_text.split('\n')
    
    questions = []
    current_q = None
    parsing_started = False
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Checking for the start marker
        if not parsing_started:
            if line == "Q1":
                parsing_started = True
            else:
                i += 1
                continue
        
        # If parsing started
        # Check for Question Marker: ^Q\d+$
        if re.match(r'^Q\d+$', line):
            if current_q:
                questions.append(current_q)
            current_q = {
                'id': line,
                'question': '',
                'options': {},
                'answers': [],
                'explanation': ''
            }
            i += 1
            # Next lines are the question text until we hit an option A.
            q_text = []
            while i < len(lines) and not re.match(r'^[A-F]\.', lines[i].strip()):
                if lines[i].strip():
                    q_text.append(lines[i].strip())
                i += 1
            current_q['question'] = ' '.join(q_text)
            continue
            
        if current_q:
            # Check for Option Marker: ^[A-F]\.
            if re.match(r'^[A-F]\.', line):
                opt_letter = line[0]
                opt_text = [line[2:].strip()] # skip "A."
                i += 1
                # Read until next option or Answer marker
                while i < len(lines) and not re.match(r'^[A-F]\.', lines[i].strip()) and not lines[i].strip().startswith('Answer:'):
                    if lines[i].strip():
                        opt_text.append(lines[i].strip())
                    i += 1
                current_q['options'][opt_letter] = ' '.join(opt_text)
                continue
                
            # Check for Answer Marker: Answer: [A-F]+
            if line.startswith('Answer:'):
                ans_text = line.replace('Answer:', '').strip()
                # Find all letters A-F in the answer text
                answers = re.findall(r'[A-F]', ans_text)
                current_q['answers'] = answers
                
                i += 1
                # Read explanation until next question marker
                exp_text = []
                while i < len(lines) and not re.match(r'^Q\d+$', lines[i].strip()):
                    if lines[i].strip():
                        exp_text.append(lines[i].strip())
                    i += 1
                current_q['explanation'] = ' '.join(exp_text)
                continue
                
        i += 1
        
    if current_q:
        questions.append(current_q)
        
    return questions

def main():
    st.title("PDF2Quiz - Interactive Exam Prep")
    
    # Sidebar
    with st.sidebar:
        st.header("Upload PDF")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        
        if uploaded_file is not None:
            if 'parsed_pdf_name' not in st.session_state or st.session_state.parsed_pdf_name != uploaded_file.name:
                with st.spinner("Parsing PDF..."):
                    file_bytes = uploaded_file.read()
                    questions = parse_pdf(file_bytes)
                    st.session_state.questions = questions
                    st.session_state.parsed_pdf_name = uploaded_file.name
                    st.session_state.current_index = 0
                    st.session_state.show_answer = False
                st.success(f"Parsed {len(questions)} questions!")
                
        if 'questions' in st.session_state and st.session_state.questions:
            total_q = len(st.session_state.questions)
            st.divider()
            st.write(f"**Total Questions:** {total_q}")
            
            # Progress tracking
            progress = (st.session_state.current_index + 1) / total_q
            st.progress(progress)
            
            # Jump to question
            jump_num = st.number_input("Jump to Question No.", min_value=1, max_value=total_q, 
                                       value=st.session_state.current_index + 1)
            if jump_num - 1 != st.session_state.current_index:
                if st.button("Go"):
                    st.session_state.current_index = jump_num - 1
                    st.session_state.show_answer = False
                    st.rerun()

    # Main Area
    if 'questions' in st.session_state and st.session_state.questions:
        idx = st.session_state.current_index
        q = st.session_state.questions[idx]
        
        st.subheader(f"Question {idx + 1} of {len(st.session_state.questions)} ({q['id']})")
        st.write(q['question'])
        
        st.write("---")
        st.write("**Options:**")
        
        # User Selection
        is_multi = len(q['answers']) > 1
        user_answers = []
        
        if is_multi:
            st.info(f"Select {len(q['answers'])} answers.")
            for opt_key, opt_val in q['options'].items():
                if st.checkbox(f"**{opt_key}.** {opt_val}", key=f"check_{idx}_{opt_key}"):
                    user_answers.append(opt_key)
        else:
            opts = [f"{opt_key}. {opt_val}" for opt_key, opt_val in q['options'].items()]
            if opts:
                selected = st.radio("Choose one answer:", opts, index=None, key=f"radio_{idx}")
                if selected:
                    user_answers.append(selected[0]) # The letter
        
        # Action Buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("Previous") and idx > 0:
                st.session_state.current_index -= 1
                st.session_state.show_answer = False
                st.rerun()
        with col2:
            if st.button("Next") and idx < len(st.session_state.questions) - 1:
                st.session_state.current_index += 1
                st.session_state.show_answer = False
                st.rerun()
                
        st.write("---")
        if st.button("Check Answer"):
            st.session_state.show_answer = True
            
        if st.session_state.get('show_answer', False):
            # Validate
            correct_answers = sorted(q['answers'])
            user_answers = sorted(user_answers)
            
            if user_answers == correct_answers:
                st.success("Correct! 🎉")
            else:
                st.error(f"Incorrect. The correct answer is **{', '.join(correct_answers)}**.")
                
            with st.expander("Show Explanation", expanded=True):
                if q['explanation']:
                    st.write(q['explanation'])
                else:
                    st.write("No explanation available.")

    else:
        st.info("Please upload a PDF file from the sidebar to begin.")

if __name__ == "__main__":
    main()
