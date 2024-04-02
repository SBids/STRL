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
import openpyxl
import random

fifo_suppression_value = 'fifo_suppression_value' #we don't care if this file is chaged because we write to this file
fifo_object_details = 'fifo_object_details'
num = 0
reward_history = []



def generate_positional_embedding(text):
  print("Text ", text)
  alphabet = string.ascii_lowercase
  digits = string.digits
  symbols = "!@#$%^&*()_-+={}[]|\:;'<>?,./\""
  vocab = alphabet + digits + symbols
  embedding_dimension = 64
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
  previous_suppression = 0
  
  load_checkpoint = True
  if load_checkpoint:
    agent.load_models()
  
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
      result_ms = '/'.join(states_values) 
      result = result_ms.split(' ')[0]
      prefix_name = states_dict["name"]
      embedding_start = time.time()
      embeddings = generate_positional_embedding(result)
      embedding_end = time.time()
      # print("The embedding time is ", (embedding_end - embedding_start)*1000)
      new_embeddings = tf.convert_to_tensor([embeddings], dtype=tf.float32)
      action = 29
   
      # action = round(agent.choose_action(new_embeddings),2) + random.randint(1, 5)
      previous_suppression = action
      # print("Previous suppression", action)
      wait_time = states_dict["suppression_time"].split(' ')[0]
      write_pipe = os.open(fifo_object_details, os.O_WRONLY)  
      response = "{}".format(action)
      os.write(write_pipe, response.encode())
      os.close(write_pipe)
      print("Counter in RL: ", counter, states_dict["name"], wait_time)

      # if prefix_name in experience_dict.keys():
      #   dc = states_dict["ewma_dc"]
      #   reward = 3 -float(dc) - float(wait_time)/20

      #   print("Reward ", reward, "for the action ", wait_time)        
      #   done = 0
      #   previous_state = experience_dict[prefix_name]
      #   current_state = new_embeddings
      #   train_start = time.time()
      #   agent.learn(previous_state, reward, current_state, done)
      #   train_end = time.time()
      #   # print("The learning time taken is: ", (train_end - train_start)*1000)
      #   reward_history.append(reward)
      end_time = time.time()
      print("Execution period ", (end_time - start_time)*1000)
      # experience_dict[prefix_name] = new_embeddings
      counter = counter + 1
      
      # if counter%200 == 0:
      #   print("Saving the model weight")
      #   agent.save_models()
      # if counter == 900:
      #   try:
      #     with open('/home/dh127-pc4/workspace/STRL/files/reward.txt', 'w') as file:
      #       for item in reward_history:
      #         file.write(f"{item}\n")
      #     print(f"Successful !!")
      #   except Exception as e:
      #     print(f"Error: {e}")
       
    except Exception as e:
      print ("exception: ", e)

   

  
  