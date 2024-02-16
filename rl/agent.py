import tensorflow as tf
from tensorflow.keras.optimizers import Adam
import tensorflow_probability as tfp
from network import ActorCriticNetwork
import os

import tensorflow.keras as keras

chkpt_dir_path = "/home/dh127-pc4/workspace/STRL/rl/model3"

class Agent:
  def __init__(self, gamma=0.97, n_actions=1, chkpt_dir=chkpt_dir_path):
    self.gamma = gamma
    self.n_actions = n_actions
    self.actor_critic = ActorCriticNetwork(n_actions=n_actions)

    self.actor_critic.compile(optimizer=Adam(learning_rate=0.0002))
    self.checkpoint_file = os.path.join(chkpt_dir_path, '_actor_critic_')
    # exception:  'Agent' object has no attribute 'checkpointfile'

  def choose_action(self, observation):
    _, mu, sigma = self.actor_critic(observation)
    action_distribution = tfp.distributions.Normal(loc=mu, scale=0.01)
    raw_action = action_distribution.sample()
    action = tf.clip_by_value(raw_action, clip_value_min=5.0, clip_value_max=300.00)
    log_prob = action_distribution.log_prob(action)
    self.action = action
    action = action[0]
    print("Action !!!", action.numpy()[0])
    return action.numpy()[0]

  def get_reward(self, ewma_duplicate_count, rtt, srtt, alpha=0.5, beta=0.4, gamma=0.3):
    if rtt is not None:
        reward = -(alpha * float(ewma_duplicate_count) + beta * rtt + gamma * (rtt - srtt))
    else:
        reward = -(alpha * float(ewma_duplicate_count) + gamma * srtt)
    return reward

  def learn(self, state, reward, state_, done):
    state = tf.convert_to_tensor([state], dtype=tf.float32)
    reward = tf.convert_to_tensor([reward], dtype=tf.float32)    
    done = tf.convert_to_tensor([int(done)], dtype=tf.float32)    
    '''
    GradientTape is a TensorFlow tool that is used for automatic differentiation. 
    It allows you to record operations that are performed on tensors, and then 
    compute the gradients of any variables with respect to the recorded operations.

    GradientTape is often used to compute the gradients of the policy and value functions 
    with respect to the loss function, which allows the weights of the neural network 
    to be updated in a direction that improves the performance of the agent.
    '''
    with tf.GradientTape() as tape:
      value, mu, sigma = self.actor_critic(state)
      value_, _, _ = self.actor_critic(state_)
      td_error = reward + self.gamma * value_ * (1 - done) -value
      advantage = td_error
      dist = tfp.distributions.Normal(loc=mu, scale=sigma)
      log_prob = dist.log_prob(self.action)
      actor_loss = -log_prob * tf.stop_gradient(advantage)
      critic_loss = tf.square(td_error)
      loss = actor_loss + critic_loss
    # Compute gradients and update weights
    gradients = tape.gradient(loss, self.actor_critic.trainable_variables)
    # for var in self.actor_critic.trainable_variables:
    #   print("Trainable variables", var)
    self.actor_critic.optimizer.apply_gradients(zip(gradients, self.actor_critic.trainable_variables))
  
  def save_models(self):
    print("Saved model!!!")
    self.actor_critic.save_weights(self.checkpoint_file)

  def load_models(self):
    self.actor_critic.load_weights(self.checkpoint_file)
    print("The model is loaded")
    

