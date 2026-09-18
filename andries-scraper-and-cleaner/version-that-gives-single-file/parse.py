import sys
import json

from ollama import chat
from ollama import ChatResponse

# 
# Maximum paragraph size
# The paragraph will be send, once we pass this threshold, so dont set it to its absolute limits
# 
MAX_LENGTH = 4000

# 
# Check if input file is given
# 
if(len(sys.argv) != 2):
  raise Exception("Usage: python parse.py path/to/input.json")


# 
# Function that sends a section to Ollama
# 
def sendSectionToLLM(buffer):
  stream =  chat(
    model='qwen3:4b',
    # model='gemma3:4b',
    messages=[
      {
        'role': 'system',
        'content': "You get a section of a submission guideline from a scientific publisher and you want to publish a manuscript. Tell me what the maximal length of the abstract may be. Also tell me igf there is a total word limit. Give the answer as json, like {abstract: ... , total: ...}. If no information is given or if there is no limit, give -1 as answer. Do not worry you get all the information. In later runs you get other sections to read."
      },
      {
        'role': 'user',
        'content': buffer
      }
    ],
    stream=True,
  )

  # TODO: For fun we see its thinking. This should be disabled in the live version.
  in_thinking = False
  content = ''
  thinking = ''
  print("\033[94m") # Set terminal color to blue
  for chunk in stream:
    if chunk.message.thinking:
      if not in_thinking:
        in_thinking = True
        print('Thinking:\n', end='', flush=True)
      print(chunk.message.thinking, end='', flush=True)
      # accumulate the partial thinking 
      thinking += chunk.message.thinking
    elif chunk.message.content:
      if in_thinking:
        in_thinking = False
      # accumulate the partial content
      content += chunk.message.content
  print("\033[0m") # reset terminal color
  return content

def parseSection(result, section):
  try:
    obj = json.loads(section)

    abstractLength = obj["abstract"]
    totalLength = obj["total"]

    result["abstract"] = max(result["abstract"], abstractLength)
    result["total"] = max(result["total"], totalLength)

  except:
    print("-- Unable to parse section") 
    print(section)
  
  return result


# 
# Actual main function
# 
result = {
  "abstract": -1,
  "total": -1
}

with open(sys.argv[1]) as f:
  data = json.load(f)

  #
  # We loop through each item.
  # In each item we break up the markdown text in several sections.
  # Each section we put into a buffer that we send to a (local) LLM
  # After that we combina all the JSON into a single object.
  # 
  for item in data:
    print("- Running " + item["url"])
    markdown = item["markdown"].splitlines();

    counter = 0;
    buffer = ""
    for line in markdown:
      if(len(line.strip()) == 0):
        if(counter > MAX_LENGTH):
          section = sendSectionToLLM(buffer)
          result = parseSection(result, section)

          # reset buffer
          buffer = ""
          counter = 0
        else:
          # Add line to buffer
          buffer += "\n" + line
          counter += len(line) + 1
        pass
      else:
        # Add line to buffer
        buffer += "\n" + line
        counter += len(line) + 1
      

    if(counter != 0):
      section = sendSectionToLLM(buffer)
      result = parseSection(result, section)

    # TODO: Save the information into some system. We now print it to the screen.
    print(result);
    print("")