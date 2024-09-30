import pandas as pd
import requests
import json
from io import StringIO
from abc import ABC, abstractmethod
from IPython.display import display, clear_output
from ipywidgets import (Textarea, Button, VBox, HBox, Layout, IntProgress, 
                        Tab, IntText, Label, HTML as HTMLWidget)

# Data Interface
class DataInterface(ABC):
    @abstractmethod
    def get_dataframe(self):
        pass

    @abstractmethod
    def get_table_schema(self):
        pass

# CSV data implementation for a single CSV file
class CSVData(DataInterface):
    def __init__(self, csv_content, dataframe_name='data'):
        """
        csv_content: The content of the CSV file as a string.
        dataframe_name: The name to assign to the DataFrame.
        """
        self.csv_content = csv_content
        self.dataframe_name = dataframe_name
        self.dataframe = None
        self.load_dataframe()

    def load_dataframe(self):
        self.dataframe = pd.read_csv(StringIO(self.csv_content))

    def get_dataframe(self):
        return self.dataframe

    def get_table_schema(self):
        columns = [(None, col_name, str(dtype)) for col_name, dtype in zip(self.dataframe.columns, self.dataframe.dtypes)]
        return (self.dataframe_name, columns)

# UI Interface (same as before)
class UIInterface(ABC):
    @abstractmethod
    def display_question(self, question, schema):
        pass

    @abstractmethod
    def get_user_code(self):
        pass

    @abstractmethod
    def display_results(self, user_result, correct_result):
        pass

    @abstractmethod
    def display_error(self, message):
        pass

    @abstractmethod
    def clear_code(self):
        pass

    @abstractmethod
    def try_again(self):
        pass

    @abstractmethod
    def next_question(self):
        pass

    @abstractmethod
    def show_hint(self, hint):
        pass

    @abstractmethod
    def update_progress(self, current_index, total):
        pass

    @abstractmethod
    def display_completion_message(self):
        pass

    @abstractmethod
    def focus_code_input(self):
        pass

# Ipywidgets UI implementation (modified for single DataFrame)
class IpywidgetsUI(UIInterface):
    def __init__(self):
        self.quiz = None  # Will be set later
        self.displayed = False  # To prevent multiple displays
        self.setup_ui()

    def set_quiz(self, quiz):
        self.quiz = quiz

    def setup_ui(self):
        self.progress_bar = IntProgress(min=0, max=1, value=0, description='Progress:')
        self.question_label = HTMLWidget(value='')
        
        self.text_area = Textarea(placeholder='Type your Pandas code here...', 
                                  layout=Layout(width='100%', height='150px'))
        self.submit_button = Button(description="Submit", button_style='success')
        self.clear_button = Button(description="Clear", button_style='warning')
        self.hint_button = Button(description="Hint", button_style='info')
        
        self.skip_input = IntText(value=1, min=1, layout=Layout(width='60px'))
        self.skip_button = Button(description="Skip to", button_style='info')
        self.skip_box = HBox([Label('Go to question:'), self.skip_input, self.skip_button])

        self.submit_button.on_click(lambda _: self.quiz.submit_code())
        self.clear_button.on_click(lambda _: self.clear_code())
        self.skip_button.on_click(lambda _: self.skip_to_question())
        self.hint_button.on_click(lambda _: self.quiz.show_hint())
    
        self.query_box = VBox([self.text_area, 
                               HBox([self.submit_button, self.clear_button, self.hint_button]),
                               self.skip_box])
        
        self.results_area = HTMLWidget(value='')
        self.try_again_button = Button(description="Try Again", button_style='warning')
        self.next_button = Button(description="Next Question", button_style='info')
        self.try_again_button.on_click(lambda _: self.quiz.try_again())
        self.next_button.on_click(lambda _: self.quiz.next_question())
        
        self.results_box = VBox([self.results_area, HBox([self.try_again_button, self.next_button])])
        
        self.tab = Tab(children=[self.query_box, self.results_box])
        self.tab.set_title(0, 'Code')
        self.tab.set_title(1, 'Results')
        
        self.main_box = VBox([self.progress_bar, self.question_label, self.tab])

    def display_question(self, question, schema):
        clear_output(wait=True)
        schema_html = self.render_table_schema(schema)
        self.question_label.value = (f"<h3>Question {self.quiz.current_index + 1} of {self.quiz.total_questions}:</h3>"
                                     f"<p>{question}</p>{schema_html}")
        self.text_area.value = ''
        self.submit_button.disabled = False
        self.skip_input.max = self.quiz.total_questions
        self.tab.selected_index = 0  # Switch to Code tab
        if not self.displayed:
            display(self.main_box)
            self.displayed = True

    def get_user_code(self):
        return self.text_area.value.strip()

    def display_results(self, user_result, correct_result):
        user_rows, user_cols = user_result.shape
        correct_rows, correct_cols = correct_result.shape
        count_info = (f"<p>Your code returned a DataFrame with {user_rows} rows and {user_cols} columns. "
                      f"The expected result has {correct_rows} rows and {correct_cols} columns.</p>")
        
        if user_result.equals(correct_result):
            feedback = "<h3 style='color: green;'>Correct! Your code produced the expected result.</h3>"
            self.next_button.disabled = False
            self.try_again_button.disabled = True
        else:
            feedback = "<h3 style='color: red;'>Incorrect. Please try again.</h3>"
            self.next_button.disabled = True
            self.try_again_button.disabled = False

        results_html = feedback + count_info
        results_html += "<h4>Your Results (first five rows):</h4>"
        results_html += user_result.head().to_html(index=False)
        results_html += "<h4>Expected Results (first five rows):</h4>"
        results_html += correct_result.head().to_html(index=False)
        
        self.results_area.value = results_html
        self.tab.selected_index = 1  # Switch to Results tab

    def display_error(self, message):
        self.results_area.value = f"<h3 style='color: red;'>Error: {message}</h3>"
        self.tab.selected_index = 1  # Switch to Results tab

    def clear_code(self):
        self.text_area.value = ''

    def try_again(self):
        self.tab.selected_index = 0  # Switch back to Code tab

    def next_question(self):
        self.quiz.next_question()

    def show_hint(self, hint):
        self.results_area.value = f"<h3>Hint:</h3><pre>{hint}</pre>"
        self.tab.selected_index = 1  # Switch to Results tab

    def update_progress(self, current_index, total):
        self.progress_bar.max = total
        self.progress_bar.value = current_index

    def focus_code_input(self):
        pass  # Not implemented in ipywidgets

    def render_table_schema(self, schema):
        dataframe_name, columns = schema
        schema_html = "<h3>Available DataFrame:</h3><ul>"
        column_info = ", ".join(f"{column[1]} ({column[2]})" for column in columns)
        schema_html += f"<li><b>{dataframe_name}</b>: {column_info}</li>"
        schema_html += "</ul>"
        return schema_html

    def skip_to_question(self):
        new_index = self.skip_input.value - 1
        if 0 <= new_index < self.quiz.total_questions:
            self.quiz.current_index = new_index
            self.quiz.display_current_question()
        else:
            self.display_error(f"Invalid question number. Please enter a number between 1 and {self.quiz.total_questions}.")

    def display_completion_message(self):
        self.main_box.children = [HTMLWidget(value="<h2>All questions completed. Well done!</h2>")]
        clear_output(wait=True)
        display(self.main_box)

# Main Quiz class (modified for single DataFrame)
class Quiz:
    def __init__(self, data: DataInterface, ui: UIInterface, questions, answers):
        self.data = data
        self.ui = ui
        self.questions = questions
        self.answers = answers
        self.current_index = 0
        self.total_questions = len(questions)
        self.ui.set_quiz(self)
        self.dataframe_name = self.data.dataframe_name

    def start(self):
        self.display_current_question()

    def display_current_question(self):
        schema = self.data.get_table_schema()
        question = self.questions[self.current_index]
        self.ui.display_question(question, schema)
        self.ui.update_progress(self.current_index + 1, self.total_questions)

    def submit_code(self):
        user_code = self.ui.get_user_code()
        dataframe = self.data.get_dataframe()
        # Prepare the execution environment
        exec_env = {'pd': pd, self.dataframe_name: dataframe}
        try:
            # Execute user's code
            exec(user_code, {}, exec_env)
            if 'result' not in exec_env:
                self.ui.display_error("Please assign your result to a variable named 'result'.")
                return
            user_result = exec_env['result']
            if not isinstance(user_result, pd.DataFrame):
                self.ui.display_error("Your 'result' variable must be a Pandas DataFrame.")
                return
            # Execute correct answer code
            answer_code = self.answers[self.current_index]
            answer_env = {'pd': pd, self.dataframe_name: dataframe}
            exec(answer_code, {}, answer_env)
            correct_result = answer_env['result']
            # Compare the results
            self.ui.display_results(user_result.reset_index(drop=True), correct_result.reset_index(drop=True))
        except Exception as e:
            self.ui.display_error(f"Error executing your code: {str(e)}")

    def next_question(self):
        self.current_index += 1
        if self.current_index < self.total_questions:
            self.display_current_question()
        else:
            self.ui.display_completion_message()

    def try_again(self):
        self.ui.clear_code()
        self.ui.focus_code_input()

    def show_hint(self):
        correct_code = self.answers[self.current_index]
        # Provide a hint by masking some parts of the code
        hint_lines = correct_code.strip().split('\n')
        masked_lines = []
        for line in hint_lines:
            if line.strip().startswith('#'):
                masked_lines.append(line)
            else:
                tokens = line.split()
                masked_line = ' '.join(token if i % 2 == 0 else '_____' for i, token in enumerate(tokens))
                masked_lines.append(masked_line)
        hint = '\n'.join(masked_lines)
        self.ui.show_hint(hint)

# Functions to load quizzes by ID or URL
def pandas_quiz_from_id(quiz_id="employees"):
    if quiz_id == "employees":
        csv_url = "https://raw.githubusercontent.com/yourusername/datasets/main/employees.csv"
        json_url = "https://raw.githubusercontent.com/yourusername/quizzes/main/employees_quiz.json"
        dataframe_name = "data"
    elif quiz_id == "sales":
        csv_url = "https://raw.githubusercontent.com/yourusername/datasets/main/sales.csv"
        json_url = "https://raw.githubusercontent.com/yourusername/quizzes/main/sales_quiz.json"
        dataframe_name = "data"
    else:
        print(f"Quiz ID '{quiz_id}' not recognized.")
        return

    pandas_quiz_url(csv_url, json_url, dataframe_name)

def pandas_quiz_url(csv_url, json_url, dataframe_name='data'):
    # Load CSV data from URL
    response = requests.get(csv_url)
    if response.status_code != 200:
        print(f"Failed to download CSV data from {csv_url}")
        return
    csv_content = response.text

    # Load quiz data from URL
    response = requests.get(json_url)
    if response.status_code != 200:
        print(f"Failed to download quiz data from {json_url}")
        return
    quiz_data = json.loads(response.text)

    questions = [item['question'] for item in quiz_data]
    answers = [item['answer'] for item in quiz_data]

    # Initialize data, UI, and quiz
    data = CSVData(csv_content, dataframe_name)
    ui = IpywidgetsUI()
    quiz = Quiz(data, ui, questions, answers)
    quiz.start()
