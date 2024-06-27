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

def plot_learning_curve(x, scores, figure_file):
  running_avg = np.zeros(len(scores))
  for i in range(len(running_avg)):
    running_avg[i] = np.mean(scores[max(0, i-100):(i+1)])
  plt.plot(x, running_avg)
  plt.title('Running average of previous 100 scores')
  plt.savefig(figure_file)
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
      prefix_name = '/'.join(states_values[1].split('/')[:-1])
      states_values[1] = prefix_name
      result = '/'.join(states_values) 
      print("Result ", states_dict)
      embedding_start = time.time()
      embeddings = generate_positional_embedding(result)
      embedding_end = time.time()
      print("The embedding time is ", (embedding_end - embedding_start)*1000)
      new_embeddings = tf.convert_to_tensor([embeddings], dtype=tf.float32)
      if states_dict["seg_name"] in seg_dict.keys():        
        action = seg_dict[states_dict["seg_name"]]
        # action = round(agent.choose_action(new_embeddings),2)
        write_pipe = os.open(fifo_object_details, os.O_WRONLY)  
        response = "{}".format(action)
        os.write(write_pipe, response.encode())
        os.close(write_pipe)      
      else:
        action = round(agent.choose_action(new_embeddings),2)
        seg_dict[states_dict["seg_name"]] = action     
        write_pipe = os.open(fifo_object_details, os.O_WRONLY)  
        response = "{}".format(action)
        os.write(write_pipe, response.encode())
        os.close(write_pipe)
        if prefix_name in experience_dict.keys():
          dc = states_dict["ewma_dc"]
          reward = 13 - float(dc)
          score += reward
          
          done = 0
          previous_state = experience_dict[prefix_name]
          current_state = new_embeddings
          train_start = time.time()
          # agent.learn(previous_state, reward, current_state, done)

          train_end = time.time()
          print("The learning time taken is: ", (train_end - train_start)*1000)
          reward_history.append(score)
          avg_score = np.mean(reward_history[-100:])

     

      end_time = time.time()
      print("Execution period ", (end_time - start_time)*1000)
      experience_dict[prefix_name] = new_embeddings
      counter = counter + 1
      
      # if counter == 8000:
      #   print("Saving the model weight")
        # agent.save_models()
      # x = [i+1 for i in range(counter)]
      # plot_learning_curve(x, reward_history, 'cartpole_1e-5_1024x512_1800games.png')
    except Exception as e:
      print ("exception: ", e)

    
  





       # print("Segment dictionary ", seg_dict)
      # print("Experience dict ", experience_dict)
      # if len(reward_history) >= 100:
      #   average_reward = sum(reward_history[-100:])/100
      #   threshold = 12
      #   if average_reward >= threshold:
      #     agent.save_models()

  
  