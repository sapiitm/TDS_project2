# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ipykernel",
#     "matplotlib",
#     "numpy",
#     "pandas",
#     "requests",
#     "seaborn",
# ]
# ///

import sys
import requests
import json
# from google.colab import userdata
import os
import glob
import base64
from io import StringIO
import pandas as pd

token = os.environ["AIPROXY_TOKEN"]

# give unique value counts of categorical column



## to be used in open ai function calling
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_categorical_numerical_column_name",
            "description": "Get the categorical column names that can be useful in plotting python seaborn pairplot with hue parameter for data visualisation, when the users ask help me with pairplot.Suggest the columns having unique value less than 15 else visualization is not possible. For numerical names suggest columns having data type as int or float but avoid columns having id value",
            "parameters": {
                "type": "object",
                "properties": {
                    "categorical_column": {
                        "type": "string",
                        "description": "List of categorical column names can be used in hue parameter of seaborn pairplot",
                    },
                     "numerical_column": {
                        "type": "string",
                        "description": "List of numerical column names that can be used seaborn pairplot, do not provide column names that contain  id value",
                    },
                },
                "required": ["categorical_column", "numerical_column"],
                "additionalProperties": False,
            },
        }
    }
]


# openai function calling with the above tools created

def get_categorical_numerical_column_name(categorical_column, folder,df, numerical_column):
  import seaborn as sns
  import matplotlib.pyplot as plt
  """Get the categorical column names that can be useful in plotting python seaborn pairplot with hue parameter for data visualisation, when the users ask help me with pairplot"""
  cur_dic =  os.getcwd()
  os.chdir(folder)
  print(f"num cols: {numerical_column}")
  print(f"cat colms : {categorical_column}")

  #convert the numerical column to list
  num_col = []
  for i in numerical_column.split(','):
    num_col.append(i.strip())


  try:
    for col in categorical_column.split(','):

      if col.strip() != '':
        print(f"Generating pairplot for {col}")
        plt.figure(figsize=(10, 6))

        #append the categorical column
        if df[col.strip()].nunique() <15:
          num_col.append(col.strip())
          sns.pairplot(df[num_col],corner=True,hue=col.strip())
          plt.savefig(f"paitplot_{col}.png")
          plt.close()
          print(f"pairplot generation completed")
        else:
          print(f"skipping pairplot generation as unique value of categorical column is too high")

      else:
        print(f"Generating pairplot for dataframe")
        sns.pairplot(df[num_col],corner=True)
        plt.savefig("paitplot.png")
        plt.close()
        print(f"pairplot generation completed")
  except Exception as e:
    print(f'pairplot generation has failed {e}')
  os.chdir(cur_dic)    

## function to get image from text of python code

def generate_image_from_text_input(folder,text,df):
  text = text.replace("`",'')
  text = text.replace("python",'')
  cur_dic =  os.getcwd()
  try:
    ## change the directory to store the image
    os.chdir(folder)
    exec(text)
    print('Generated image successfully')
    return 'success'
  except Exception as e:
    print(e)
    print('Generated image failed!!')
    return ('python code has failed with the error {e}')

  os.chdir(cur_dic)


def main(filename,token):
    print("Hello from project2!")
    

    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}


    df = pd.read_csv(filename,encoding='latin-1')
    filename =  filename.split('/')[-1]

    #create the folder with file name to store the results
    folder =  filename.split('/')[-1].replace('.csv','')
    try:
      os.mkdir(folder)
      print('folder created successfully')
    except:
      print('folder already present')

    current_directory = os.getcwd()
    folder = os.path.join(current_directory, folder)

    
    

    message = {}
    # Use StringIO to capture the output of df.info()
    buffer = StringIO()
    df.info(buf=buffer)
    text = buffer.getvalue()

    message['dataframe column details'] = text
    text = df.describe().to_dict()
    message['dataframe describe'] = text
    temp = ''
    text_unique = ''
    for col in df.columns:
        if df[col].dtype == 'object':  # Check for categorical columns (object dtype)
            unique_counts = df[col].nunique()
            temp = f"Unique value counts for column '{col}':\n{unique_counts}\n"
            text_unique = temp+ ' '+ text_unique
    message['dataframe categorical column'] = text_unique
      



        
    ## 1st prompt asking about python codes for chart
    data = {
        "model": "gpt-4o-mini",  # or another suitable model
        "messages": [
            {"role": "system", "content": "Will be given details of pandas dataframe named as df, write 3 python code to create charts using seaborn to visualize the data and save it as png with different names.Only share the python codes"},
            {"role": "user", "content": json.dumps(message)}

                    ]
    }

    response = requests.post("https://aiproxy.sanand.workers.dev/openai/v1/chat/completions", headers=headers, json=data)

    if response.status_code == 200:
        response_json = response.json()
        code = response_json['choices'][0]['message']['content'] # Print the date
        # print(code)
        print("Python codes to generate chart has been received from OPENAI..")

    else:
        print(f"Error: {response.status_code}")

    #call the function to create charts from code
    func_output = generate_image_from_text_input(folder,code,df)

    ##if there is failure in image generation then call the openai again
    iteration = 0
    # stop at 2nd iteration
    for i in range(2):
      if func_output != 'success':
        print(f'iteration {iteration}')
        iteration+=1
          
        ## 1st prompt asking about python codes for chart
        data = {
            "model": "gpt-4o-mini",  # or another suitable model
            "messages": [
                {"role": "system", "content": "Will be given details of pandas dataframe named as df, write 3 python code (If any column is having date value convert to pandas Datetime format) to create charts using seaborn to visualize the data and save it as png with different names.Only share the python codes"},
                {"role": "user", "content": json.dumps(message)},
                {"role": "user", "content": f"fix the below error and provide new code to generate 3 charts error: {func_output}"}
                        ]
        }

        response = requests.post("https://aiproxy.sanand.workers.dev/openai/v1/chat/completions", headers=headers, json=data)

        if response.status_code == 200:
            response_json = response.json()
            code = response_json['choices'][0]['message']['content'] # Print the date
            print(code)
            print("Python codes to generate chart has been received from OPENAI..")
            func_output = generate_image_from_text_input(folder,code,df)

        else:
            print(f"Error: {response.status_code}")
        
    ##function calling start

    

    data = {
        "model": "gpt-4o-mini",  # or another suitable model
        "messages": [
            {"role": "system", "content": "You will be given details of pandas dataframe named as df, If the user asks for help with pairplot, use the provided tools"},
            {"role": "user", "content": json.dumps(message)},
            {"role": "user", "content": "help me with seaborn pairplot"}
        ],
        "tools": tools
    }

    print("before function calling")
    response = requests.post("https://aiproxy.sanand.workers.dev/openai/v1/chat/completions", headers=headers, json=data)

    print("after function calling")

    if response.status_code == 200:
        response_json = response.json()
        # print(response_json)
        if response_json.get("choices",[{}])[0].get("finish_reason",'') == 'tool_calls':
          tool_call = response_json['choices'][0]['message']['tool_calls'][0]
          function_name = tool_call['function']['name']
          function_args = json.loads(tool_call['function']['arguments'])
          if function_name == "get_categorical_numerical_column_name":
            get_categorical_numerical_column_name(function_args.get("categorical_column"),folder,df, function_args.get("numerical_column"))
        else:
          code = response_json['choices'][0]['message']['content']

    else:
        print(f"Error: {response.status_code}")



        


    ## convert the image to base64 for open api input
    file_list = glob.glob(f"{folder}/*.png")
    image_list = []
    for image in file_list:
      print(f"encoding image {image}")
      with open(image, 'rb') as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
        image_list.append(encoded_image)

    print(f"encoding of image is completed ..")

    ## store the description of image in a list for future openai input
    image_description = []
    for image in file_list:

      data = {
          "model": "gpt-4o-mini",  # or another suitable model
          "messages": [
              {"role": "system", "content": f"You will be given an chart from {filename} dataset, get insights from this {image.split('/')[-1]} image"},
              {"role": "user", "content": [
                  {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_list[0]}",
                                                      "detail": "low"
                                                      },

                  }
              ]}
          ]
      }

      response = requests.post("https://aiproxy.sanand.workers.dev/openai/v1/chat/completions", headers=headers, json=data)

      if response.status_code == 200:
          response_json = response.json()
          image_description.append("chart name is {image} and chart decription is {response_json['choices'][0]['message']['content']}")
          print("Insights from the genrated charts done successfully...")
      else:
          print(f"Error: {response.status_code}")

    ## pass all the previous input to model to get final output
    # print(f"file_list{file_list}")
    image1 =  file_list[0].split('/')[-1]
    image2 =  file_list[1].split('/')[-1]
    image3 =  file_list[2].split('/')[-1]

 

    data = {
      "model": "gpt-4o-mini",  # or another suitable model
      "messages": [
          {"role": "system", "content": f"You will be given details {filename} , You will also be given description of 3 charts from this data.Now describe 1.The data you received, briefly 2.The analysis you carried out 3.The insights you discovered 4. The implications of your findings (i.e. what to do with the insights)"},
          {"role": "user", "content": json.dumps(message)},
          {"role": "user", "content": json.dumps(image_description)},
          # {"role": "user", "content": f"chart name is {image2} and chart description is{image_description[1]}"},
          # {"role": "user", "content": f"chart name is {image3} and chart description is{image_description[2]}"}
                  ]
  }

    response = requests.post("https://aiproxy.sanand.workers.dev/openai/v1/chat/completions", headers=headers, json=data)

    if response.status_code == 200:
        response_json = response.json()
        # print(response_json['choices'][0]['message']['content']) # Print the date
        output = response_json['choices'][0]['message']['content'] # Print the date
        print("Final content of anaylysis has been generated successfully..")
    else:
        print(f"Error: {response.status_code}")
    
    ## store the text in the README.md file

    with open(f"{folder}/README.md", 'w') as file:
      file.write(output)
      print("Program run completed successfully")


















if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]  # Get the file name from the command-line argument
        main(filename,token)
    else:
      print("Please provide a CSV filename as an argument.")

