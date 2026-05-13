import re
import csv
from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: str)->str:
    """Extract text from PDF using pypdf"""
    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
    return full_text


def clean_text(text: str) -> str:
    """Clean and normalize the extracted text"""
    # Replace multiple newlines with space
    text = re.sub(r'\n+', ' ', text)
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_gap_fill_questions(text: str) -> list:
    """Parse the gap-fill questions (like questions 16-25)"""
    questions_data = []

    # Look for patterns like "…16… [A. ideology B. phenomenon C. idea D. component]"
    # This pattern matches the gap number followed by options in brackets
    gap_pattern = re.compile(r'…(\d+)…\s*\[([^\]]+?)\]', re.IGNORECASE)

    # Find all gap-fill questions
    for match in gap_pattern.finditer(text):
        q_num = int(match.group(1))
        options_text = match.group(2)

        # Parse options from text like "A. ideology B. phenomenon C. idea D. component"
        options = {'A': '', 'B': '', 'C': '', 'D': ''}

        # Split options using letter pattern
        opt_pattern = re.compile(r'([A-D])\.\s+([^A-D]+?)(?=(?:[A-D]\.|$))', re.DOTALL)
        for opt_match in opt_pattern.finditer(options_text):
            letter = opt_match.group(1)
            opt_value = opt_match.group(2).strip()
            options[letter] = opt_value

        # Find the sentence containing this gap to create question context
        # Get text around the gap (100 chars before and after)
        gap_pos = text.find(f'…{q_num}…')
        if gap_pos != -1:
            start = max(0, gap_pos - 200)
            end = min(len(text), gap_pos + 300)
            context = text[start:end]
            # Extract the sentence or phrase before the gap
            sentences = re.split(r'[.!?]\s+', context)
            question_context = ""
            for sentence in sentences:
                if f'…{q_num}…' in sentence:
                    # Clean up the sentence
                    question_context = re.sub(r'\s+', ' ', sentence.strip())
                    break

        question_text = f"{question_context}" if question_context else f"Gap fill question {q_num}"

        questions_data.append({
            'question_number': q_num,
            'year': 2010,
            'question': question_text,
            'option1': options.get('A', ''),
            'option2': options.get('B', ''),
            'option3': options.get('C', ''),
            'option4': options.get('D', ''),
            'correct_option': ''  # Will be filled from answers
        })

    return questions_data


def parse_regular_questions(text: str) -> list:
    """Parse regular multiple choice questions"""
    questions_data = []
    lines = text.split('\n')

    current_q_num = None
    current_question = ""
    current_options = {'A': '', 'B': '', 'C': '', 'D': ''}
    in_question = False
    collecting_options = False

    for line in lines:
        line = line.strip()
        if not line or len(line) < 2:
            continue

        # Check for question number at start of line (1. through 100.)
        q_match = re.match(r'^(\d{1,3})\.\s+(.+)', line)
        if q_match:
            q_num = int(q_match.group(1))
            if q_num <= 100:  # Only questions 1-100
                # Save previous question
                if current_q_num and current_question and any(current_options.values()):
                    questions_data.append({
                        'question_number': current_q_num,
                        'year': 2010,
                        'question': current_question.strip(),
                        'option1': current_options['A'],
                        'option2': current_options['B'],
                        'option3': current_options['C'],
                        'option4': current_options['D'],
                        'correct_option': ''
                    })

                # Start new question
                current_q_num = q_num
                current_question = q_match.group(2)
                current_options = {'A': '', 'B': '', 'C': '', 'D': ''}
                in_question = True
                collecting_options = False
                continue

        # Check for options (A., B., C., D.)
        opt_match = re.match(r'^([A-D])\.\s+(.+)', line)
        if opt_match and in_question:
            letter = opt_match.group(1)
            current_options[letter] = opt_match.group(2)
            collecting_options = True
            continue

        # If in question and not an option, it might be continuation
        if in_question and current_q_num and not opt_match:
            if collecting_options and any(current_options.values()):
                # Append to the last option that has content
                for opt in ['D', 'C', 'B', 'A']:
                    if current_options[opt]:
                        current_options[opt] += " " + line
                        break
            else:
                # Append to question text
                current_question += " " + line

    # Add the last question
    if current_q_num and current_question and any(current_options.values()):
        questions_data.append({
            'question_number': current_q_num,
            'year': 2010,
            'question': current_question.strip(),
            'option1': current_options['A'],
            'option2': current_options['B'],
            'option3': current_options['C'],
            'option4': current_options['D'],
            'correct_option': ''
        })

    return questions_data


def parse_passage_questions(text: str)->List:
    """Parse passage-based questions (from passages I, II, III, IV)"""
    questions_data = []

    # Find passages
    passage_pattern = re.compile(r'## PASSAGE ([IVXLCDM]+)(.*?)(?=## PASSAGE|\Z)', re.DOTALL | re.IGNORECASE)

    for passage_match in passage_pattern.finditer(text):
        passage_content = passage_match.group(2)

        # Look for questions in the passage (numbered 1-15 typically)
        # Pattern finds question number followed by question text and options
        q_pattern = re.compile(
            r'(\d{1,2})\.\s+([^A]*?)(?:A\.\s+([^B]*?)B\.\s+([^C]*?)C\.\s+([^D]*?)D\.\s+([^\n]+?))(?=\n\d+\.|\Z)',
            re.DOTALL)

        for q_match in q_pattern.finditer(passage_content):
            q_num = int(q_match.group(1))
            q_text = q_match.group(2).strip()
            opt_a = q_match.group(3).strip() if q_match.group(3) else ''
            opt_b = q_match.group(4).strip() if q_match.group(4) else ''
            opt_c = q_match.group(5).strip() if q_match.group(5) else ''
            opt_d = q_match.group(6).strip() if q_match.group(6) else ''

            # Clean up text
            q_text = re.sub(r'\s+', ' ', q_text)

            questions_data.append({
                'question_number': q_num,
                'year': 2010,
                'question': q_text,
                'option1': opt_a,
                'option2': opt_b,
                'option3': opt_c,
                'option4': opt_d,
                'correct_option': ''
            })

    return questions_data


def extract_answers(text: str) -> dict:
    """Extract answers from the ANSWERS section"""
    answers = {}

    # Look for ANSWERS section
    answers_match = re.search(r'## ANSWERS\s+(.*?)(?=\n\n|\Z|$)', text, re.DOTALL | re.IGNORECASE)
    if answers_match:
        answers_text = answers_match.group(1)
        # Pattern for "1. A", "2. B", etc.
        answer_pattern = re.compile(r'(\d{1,3})\.\s+([A-D])')
        for match in answer_pattern.finditer(answers_text):
            q_num = int(match.group(1))
            ans = match.group(2)
            answers[q_num] = ans

    # If no ANSWERS section found, look for answers at the very end of the document
    if not answers:
        # Look for patterns like "1. A 2. B 3. C" at the end
        end_pattern = re.compile(r'(\d{1,3})\.\s+([A-D])')
        # Get last 2000 characters
        end_text = text[-2000:]
        for match in end_pattern.finditer(end_text):
            q_num = int(match.group(1))
            ans = match.group(2)
            answers[q_num] = ans

    return answers


def save_to_csv(questions_data: list, answers: dict, output_file: str) -> None:
    """Save the extracted data to CSV file with answers"""
    # Add correct answers to questions
    for q in questions_data:
        if q['question_number'] in answers:
            q['correct_option'] = answers[q['question_number']]

    # Sort by question number
    questions_data.sort(key=lambda x: x['question_number'])

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['question_number', 'year', 'question', 'option1', 'option2', 'option3', 'option4',
                      'correct_option']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for question in questions_data:
            writer.writerow(question)

    print(f"Successfully saved {len(questions_data)} questions to {output_file}")


def main():
    pdf_file = r"C:\Users\Olu-Ade\Desktop\Others\Use-of-English 2010.pdf"
    output_csv = r"C:\Users\Olu-Ade\Desktop\Others\jamb_2010_english_questions.csv"

    try:
        print("Extracting text from PDF using pypdf...")
        text = extract_text_from_pdf(pdf_file)

        if not text or not text.strip():
            print("Error: No text was extracted from the PDF.")
            print("The PDF might be scanned or have no selectable text.")
            return

        print(f"✓ Extracted {len(text)} characters of text")

        # Preview first 1500 characters to see structure
        print("\n" + "=" * 60)
        print("PREVIEW OF EXTRACTED TEXT (first 1500 chars):")
        print("=" * 60)
        print(text[:1500])
        print("=" * 60)

        # Extract answers
        print("\n Extracting answers...")
        answers = extract_answers(text)
        print(f"Found {len(answers)} answers")
        if answers:
            print(f"Sample answers: {dict(list(answers.items())[:10])}")

        # Parse different types of questions
        all_questions = []

        # Parse passage-based questions
        print("\n Parsing passage-based questions...")
        passage_questions = parse_passage_questions(text)
        print(f"Found {len(passage_questions)} passage questions")
        all_questions.extend(passage_questions)

        # Parse gap-fill questions (16-25)
        print("\n Parsing gap-fill questions...")
        clean_text_content = clean_text(text)
        gap_questions = parse_gap_fill_questions(clean_text_content)
        print(f"Found {len(gap_questions)} gap-fill questions")
        all_questions.extend(gap_questions)

        # Parse regular questions
        print("\n Parsing regular questions...")
        regular_questions = parse_regular_questions(text)
        print(f"Found {len(regular_questions)} regular questions")
        all_questions.extend(regular_questions)

        # Remove duplicates (keep first occurrence of each question number)
        unique_questions = {}
        for q in all_questions:
            if q['question_number'] not in unique_questions:
                unique_questions[q['question_number']] = q

        final_questions = list(unique_questions.values())
        final_questions.sort(key=lambda x: x['question_number'])

        print(f"\n{'=' * 60}")
        print(f"SUMMARY:")
        print(f"{'=' * 60}")
        print(f"Total unique questions extracted: {len(final_questions)}")
        print(f"Expected: 100 questions")

        # Save to CSV
        save_to_csv(final_questions, answers, output_csv)

        # Display sample
        if final_questions:
            print("\n✓ SAMPLE OF EXTRACTED DATA (first 5 questions):")
            print("-" * 60)
            for q in final_questions[:5]:
                print(f"\nQ{q['question_number']}: {q['question'][:150]}")
                if q['option1']:
                    print(f"   A: {q['option1'][:80]}")
                if q['option2']:
                    print(f"   B: {q['option2'][:80]}")
                if q['option3']:
                    print(f"   C: {q['option3'][:80]}")
                if q['option4']:
                    print(f"   D: {q['option4'][:80]}")
                print(f"   ✓ Correct: {q['correct_option'] if q['correct_option'] else 'Not found'}")

        # Show which question numbers are missing
        extracted_nums = set([q['question_number'] for q in final_questions])
        expected_nums = set(range(1, 101))
        missing_nums = expected_nums - extracted_nums
        if missing_nums:
            print(f"\n Missing question numbers: {sorted(missing_nums)[:20]}...")
            print(f"   Total missing: {len(missing_nums)}")

    except FileNotFoundError:
        print(f" Error: Could not find the file '{pdf_file}'")
        print("Please check if the file path is correct")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
