import os
import time
from sys import argv, exit
import string
import json
import errno
from agent import Agent
import numpy as np
import tensorflow as tf
from pathlib import Path as p


fifo_suppression_value = 'fifo_suppression_value' #we don't care if this file is chaged because we write to this file
fifo_object_details = 'fifo_object_details'
num = 0
import numpy as np
import matplotlib.pyplot as plt

def generate_positional_embedding(text):
  alphabet = string.ascii_lowercase
  digits = string.digits
  symbols = "!@#$%^&*()_-+={}[]|\:;'<>?,./\""
  vocab = alphabet + digits + symbols
  embedding_dimension = 80
  embedding = []

  for idx, char in enumerate(text.lower()):
    if char in vocab:
      char_idx = vocab.index(char)
      embedding.append(char_idx)
  while len(embedding) < embedding_dimension:
      embedding.append(0)
  embedding = embedding[:embedding_dimension]
  return(embedding)

experience_dict = {}
seg_dict = {}
done = 0
learn_count = 1
reward_history = []
score = 0


if __name__ == "__main__":
  print("Printing main function")
  try:
    os.mkfifo(fifo_object_details, mode=0o777)
  except OSError as oe:
    if oe.errno != errno.EEXIST:
      print("File does not exist!!!")
      raise

  counter = 1 
  agent = Agent()
  score = 0
  previous_time_i = 0
  previous_time_d = 0
  previous_dc = 1
  
  
  # load_checkpoint = False

  # if load_checkpoint:
  #   agent.load_models()
  
  while True:
    try:
      start_time = time.time()
      read_pipe = os.open(fifo_object_details, os.O_RDONLY)
      bytes = os.read(read_pipe, 1024)
      os.close(read_pipe)
      if len(bytes) == 0:
        print("length of byte is zero")
        break
      states_string = bytes.decode() 
      states_dict = json.loads(states_string)   
      states_values = [str(value) for value in states_dict.values()]
 

      result = '/'.join(states_values) 
      result = result.split(" ")[0]
      prefix_name_with_packet = states_dict['name']+'/'+states_dict['type']
      embeddings = generate_positional_embedding(result)
      new_embeddings = tf.convert_to_tensor([embeddings], dtype=tf.float32)
      action = int(agent.choose_action(new_embeddings))
   
     
      write_pipe = os.open(fifo_object_details, os.O_WRONLY)  
      response = "{}".format(action)
      os.write(write_pipe, response.encode())
      os.close(write_pipe)
      
      print("State with action", states_dict, action)
    
     
    except Exception as e:
      print ("exception: ", e)

   

