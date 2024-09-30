import pandas as pd
import requests
import json
from io import StringIO
from abc import ABC, abstractmethod
from IPython.display import display, clear_output
from ipywidgets import (Textarea, Button, VBox, HBox, Layout, IntProgress, 
                        Tab, IntText, Label, HTML as HTMLWidget, Output)

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

    def load_dataframe(self):
        self.dataframe = pd.read_csv(StringIO(self.csv_content))

    def get_dataframe(self):
        return self.dataframe

    def get_table_schema(self):
        columns = [(None, col_name, str(dtype)) for col_name, dtype in zip(self.dataframe.columns, self.dataframe.dtypes)]
        return (self.dataframe_name, columns)

# UI Interface
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
    def display_results_non_df(self, user_result):
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
    def show_hint(self):
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
        # Progress bar and question label
        self.progress_bar = IntProgress(min=0, max=1, value=0, description='Progress:')
        self.question_label = HTMLWidget(value='')
        
        # Text area for code input
        self.text_area = Textarea(placeholder='Type your Pandas code here...', 
                                  layout=Layout(width='100%', height='150px'))
        self.submit_button = Button(description="Submit", button_style='success')
        self.clear_button = Button(description="Clear", button_style='warning')
        self.hint_button = Button(description="Hint", button_style='info')
        
        # Skip question functionality
        self.skip_input = IntText(value=1, min=1, layout=Layout(width='60px'))
        self.skip_button = Button(description="Skip to", button_style='info')
        self.skip_box = HBox([Label('Go to question:'), self.skip_input, self.skip_button])

        # Button actions
        self.submit_button.on_click(lambda _: self.quiz.submit_code())
        self.clear_button.on_click(lambda _: self.clear_code())
        self.skip_button.on_click(lambda _: self.skip_to_question())
        self.hint_button.on_click(lambda _: self.quiz.show_hint())
    
        # Query (code input) box
        self.query_box = VBox([self.text_area, 
                               HBox([self.submit_button, self.clear_button, self.hint_button]),
                               self.skip_box])
        
        # Results area
        self.results_area = HTMLWidget(value='')
        self.try_again_button = Button(description="Try Again", button_style='warning')
        self.next_button = Button(description="Next Question", button_style='info')
        self.try_again_button.on_click(lambda _: self.quiz.try_again())
        self.next_button.on_click(lambda _: self.quiz.next_question())
        
        self.results_box = VBox([self.results_area, HBox([self.try_again_button, self.next_button])])

        # Directions area
        directions_html = """
        <h3>Directions:</h3>
        <ul>
            <li>Use the DataFrame <code>data</code> to perform the required operations.</li>
            <li>Assign your final result to a variable named <code>result</code>.</li>
            <li>Use the specific Pandas method mentioned in the hint.</li>
            <li>Your code should be a single line, e.g., <code>result = data.head()</code>.</li>
            <li>Click <strong>Submit</strong> to check your answer.</li>
            <li>If you need help, click <strong>Hint</strong> to get a hint.</li>
            <li>Use the <strong>Directions</strong> tab anytime to review these instructions.</li>
        </ul>
        """
        self.directions_area = HTMLWidget(value=directions_html)

        # Tabs
        self.tab = Tab()
        self.tab.children = [self.query_box, self.results_box, self.directions_area]
        self.tab.set_title(0, 'Question')
        self.tab.set_title(1, 'Results')
        self.tab.set_title(2, 'Directions')
        
        self.main_box = VBox([self.progress_bar, self.question_label, self.tab])

    def display_question(self, question, schema):
        clear_output(wait=True)
        schema_html = self.render_table_schema(schema)
        self.question_label.value = (f"<h3>Question {self.quiz.current_index + 1} of {self.quiz.total_questions}:</h3>"
                                     f"<p>{question}</p>{schema_html}")
        self.text_area.value = ''
        self.submit_button.disabled = False
        self.skip_input.max = self.quiz.total_questions
        self.tab.selected_index = 0  # Switch to Question tab
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
        results_html += "<h4>Your Result (first five rows):</h4>"
        results_html += user_result.head().to_html(index=False)
        results_html += "<h4>Expected Result (first five rows):</h4>"
        results_html += correct_result.head().to_html(index=False)
        
        self.results_area.value = results_html
        self.tab.selected_index = 1  # Switch to Results tab

    def display_results_non_df(self, user_result):
        feedback = "<h3 style='color: green;'>Correct! Your code produced the expected result.</h3>"
        self.next_button.disabled = False
        self.try_again_button.disabled = True
        results_html = feedback + "<h4>Your Result:</h4>"
        results_html += f"<pre>{user_result}</pre>"
        self.results_area.value = results_html
        self.tab.selected_index = 1  # Switch to Results tab

    def display_error(self, message):
        self.results_area.value = f"<h3 style='color: red;'>Error: {message}</h3>"
        self.tab.selected_index = 1  # Switch to Results tab

    def clear_code(self):
        self.text_area.value = ''

    def try_again(self):
        self.tab.selected_index = 0  # Switch back to Question tab

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
        schema_html = "<h3>Available DataFrame:</h3>"
        schema_html += f"<p><code>{dataframe_name}</code> with columns:</p><ul>"
        for _, col_name, col_type in columns:
            schema_html += f"<li><b>{col_name}</b> ({col_type})</li>"
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

# Main Quiz class
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
        # Reload the data for each question
        self.data.load_dataframe()
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
            # Capture stdout to prevent unwanted prints
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                exec(user_code, {}, exec_env)
            if 'result' not in exec_env:
                self.ui.display_error("Please assign your result to a variable named 'result'.")
                return
            user_result = exec_env['result']

            # Get the expected result type for the current question
            expected_type = self.get_expected_result_type(self.current_index)

            if not isinstance(user_result, expected_type):
                self.ui.display_error(f"Your 'result' variable must be of type {expected_type.__name__}.")
                return

            # Execute correct answer code
            # Reload the data before executing the correct answer
            self.data.load_dataframe()
            dataframe = self.data.get_dataframe()
            answer_code = self.answers[self.current_index]
            answer_env = {'pd': pd, self.dataframe_name: dataframe}
            exec(answer_code, {}, answer_env)
            correct_result = answer_env['result']

            # Compare the results
            if isinstance(user_result, pd.DataFrame):
                # Compare DataFrames
                if user_result.reset_index(drop=True).equals(correct_result.reset_index(drop=True)):
                    self.ui.display_results(user_result, correct_result)
                else:
                    self.ui.display_error("Incorrect result. Please try again.")
            else:
                # Compare other types (e.g., tuples, lists)
                if user_result == correct_result:
                    self.ui.display_results_non_df(user_result)
                else:
                    self.ui.display_error("Incorrect result. Please try again.")
        except Exception as e:
            error_output = f.getvalue()
            full_error_message = f"Error executing your code: {str(e)}"
            if error_output:
                full_error_message += f"\n\nOutput:\n{error_output}"
            self.ui.display_error(full_error_message)

    def get_expected_result_type(self, question_index):
        # Define expected result types for each question
        # Adjust the expected types based on the questions
        # For simplicity, assuming all questions expect DataFrame unless specified
        non_df_questions = {2, 3}  # Adjust indices as per your questions (zero-based)
        if question_index in non_df_questions:
            if question_index == 2:
                return list  # data.columns.tolist() returns a list
            elif question_index == 3:
                return tuple  # data.shape returns a tuple
            else:
                return pd.DataFrame
        else:
            return pd.DataFrame

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
def pandas_quiz_from_id(quiz_id="example"):
    if quiz_id == "example":
        csv_url = "https://raw.githubusercontent.com/yourusername/datasets/main/data.csv"
        json_url = "https://raw.githubusercontent.com/yourusername/quizzes/main/pandas_quiz.json"
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

# Sample usage
def start_pandas_quiz():
    # Define the CSV data as a multi-line string
    data_csv = """observation_date,biome,temperature,humidity,light_level,mob_type,mob_count
2024-05-02,Swamp,23.31,95.26,9,Skeleton,12
2024-02-13,Desert,31.06,35.80,7,Zombie,2
2024-09-21,Forest,26.41,88.98,12,Zombie,1
2024-09-09,Plains,17.68,28.06,0,Skeleton,8
2024-11-01,Forest,24.24,77.49,0,Skeleton,1
"""

    # Sample quiz data (questions and answers)
    quiz_json = """[
      {
        "question": "Display the first 5 rows of the DataFrame. Use the 'head' method.",
        "answer": "result = data.head()"
      },
      {
        "question": "Display the last 5 rows of the DataFrame. Use the 'tail' method.",
        "answer": "result = data.tail()"
      },
      {
        "question": "Get the column labels of the DataFrame as a list. Use the 'columns' attribute.",
        "answer": "result = data.columns.tolist()"
      },
      {
        "question": "Retrieve the dimensions of the DataFrame (rows and columns). Use the 'shape' attribute.",
        "answer": "result = data.shape"
      },
      {
        "question": "Generate descriptive statistics for numerical columns. Use the 'describe' method.",
        "answer": "result = data.describe()"
      },
      {
        "question": "Fill any missing values in the 'light_level' column with 0. Use the 'fillna' method.",
        "answer": "result = data.fillna({'light_level': 0})"
      },
      {
        "question": "Change the data type of the 'observation_date' column to datetime. Use the 'astype' method.",
        "answer": "result = data.astype({'observation_date': 'datetime64[ns]'})"
      },
      {
        "question": "Create a new column 'temperature_celsius' by converting 'temperature' from Fahrenheit to Celsius using the formula C = (F - 32) * 5/9. Use basic arithmetic operations.",
        "answer": "result = data.assign(temperature_celsius=(data['temperature'] - 32) * 5/9)"
      },
      {
        "question": "Rename the column 'mob_type' to 'entity_type'. Use the 'rename' method.",
        "answer": "result = data.rename(columns={'mob_type': 'entity_type'})"
      },
      {
        "question": "Remove the 'humidity' column from the DataFrame. Use the 'drop' method.",
        "answer": "result = data.drop(columns=['humidity'])"
      },
      {
        "question": "Sort the DataFrame by 'temperature' in ascending order. Use the 'sort_values' method.",
        "answer": "result = data.sort_values(by='temperature')"
      },
      {
        "question": "Apply a function to 'mob_count' to classify counts greater than 5 as 'High' and others as 'Low', and create a new column 'mob_density'. Use the 'apply' method.",
        "answer": "result = data.assign(mob_density=data['mob_count'].apply(lambda x: 'High' if x > 5 else 'Low'))"
      },
      {
        "question": "Select rows where 'biome' is 'Forest'. Use the 'loc' indexer.",
        "answer": "result = data.loc[data['biome'] == 'Forest']"
      },
      {
        "question": "Select the first three rows and first two columns of the DataFrame. Use the 'iloc' indexer.",
        "answer": "result = data.iloc[:3, :2]"
      },
      {
        "question": "Select rows where 'light_level' is greater than 5. Use conditional selection.",
        "answer": "result = data[data['light_level'] > 5]"
      },
      {
        "question": "Group the DataFrame by 'mob_type' and calculate the sum of 'mob_count' for each group. Use the 'groupby' method.",
        "answer": "result = data.groupby('mob_type')['mob_count'].sum().reset_index()"
      },
      {
        "question": "Create a pivot table with 'biome' as index and 'mob_type' as columns, showing the mean 'temperature'. Use the 'pivot_table' method.",
        "answer": "result = data.pivot_table(values='temperature', index='biome', columns='mob_type', aggfunc='mean')"
      },
      {
        "question": "Perform aggregate operations to find the mean 'temperature' and the sum of 'mob_count'. Use the 'agg' method.",
        "answer": "result = data.agg({'temperature': 'mean', 'mob_count': 'sum'})"
      },
      {
        "question": "Generate descriptive statistics for all columns, including non-numeric ones. Use the 'describe' method with the 'include' parameter.",
        "answer": "result = data.describe(include='all')"
      },
      {
        "question": "Reset the index of the DataFrame after sorting it by 'humidity' in descending order. Use the 'sort_values' and 'reset_index' methods.",
        "answer": "result = data.sort_values(by='humidity', ascending=False).reset_index(drop=True)"
      }
    ]
    """

    # Load the CSV data
    data = CSVData(data_csv, dataframe_name='data')

    # Load the quiz data
    quiz_data = json.loads(quiz_json)
    questions = [item['question'] for item in quiz_data]
    answers = [item['answer'] for item in quiz_data]

    # Initialize the UI and Quiz
    ui = IpywidgetsUI()
    quiz = Quiz(data, ui, questions, answers)
    quiz.start()

# Start the quiz
start_pandas_quiz()
