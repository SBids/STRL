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

 #we don't care if this file is chaged because we write to this file
fifo_object_details = 'fifo_object_details'
num = 0
experience_dict = {}
seg_dict = {}
done = 0
learn_count = 1
reward_history = []
score = 0

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


if __name__ == '__main__':
    try:
        os.mkfifo(fifo_object_details, mode=0o777)
    except OSError as oe:
        if oe.errno != errno.EEXIST:
            print("File does not exist")
            raise

    agent = Agent()

    # do a mkdir video if you want to record video of the agent playing.
    

    print("Soft Actor Critic testing")
    best_score = 26
    score_history = []
    counter = 1 
    load_checkpoint = False

    if load_checkpoint:
        agent.load_models()

    while True:
        read_pipe = os.open(fifo_object_details, os.O_RDONLY)
        bytes = os.read(read_pipe, 1024)
        print("bytest ", bytes)
        os.close(read_pipe)
        if len(bytes) == 0:
            break
        states_dict = json.loads(bytes.decode())
        print(states_dict)
    #     states_values = [str(value) for value in states_dict.values()]
    #     prefix_name = '/'.join(states_values[1].split('/')[:-1])
    #     states_values[1] = prefix_name
    #     result = '/'.join(states_values) 
    #     embeddings = generate_positional_embedding(result)
    #     # new_embeddings = tf.convert_to_tensor([embeddings], dtype=tf.float32)

    #     done = False
    #     score = 0
    #     while not done:
    #         action = agent.choose_action(embeddings)
    #         print("Action selected ", action)
    #         write_pipe = os.open(fifo_object_details, os.O_WRONLY)
    #         response = "{}".format(action)
    #         os.write(write_pipe, response.encode())
    #         os.close(write_pipe)     
    #         # if prefix_name in experience_dict.keys():
    #         #     dc = states_dict["ewma_dc"]
    #         #     action_exp = experience_dict[prefix_name]['Action']
    #         #     reward = 26 - 2*(float(dc))
    #         #     score += reward
    #         #     observation_ = embeddings
    #         #     observation = experience_dict[prefix_name]['Embedding']
    #         #     agent.store_transition(observation, action_exp, reward, observation_, done)
    #             # if not load_checkpoint:
    #             #     agent.learn()
    #         experience_dict[prefix_name] = {'Embedding':embeddings, 'Action':action}
    #     # score_history.append(score)
    #     # avg_score = np.mean(score_history[-100:])

    #     # if avg_score > best_score:
    #     #     best_score = avg_score
    #     #     if not load_checkpoint:
    #     #         agent.save_models()
    #     # print('episode {} score {:.1f} avg_score {:.1f}'.
    #     #       format(counter, score, avg_score))
    #     counter += 1

    