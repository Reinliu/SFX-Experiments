import librosa
import numpy as np
import json
import os
from datetime import datetime
import tensorflow as tf
import tensorflow_io as tfio
clipBelow = -10
audio_size_samples = 16384

def normalize(specs):
    max_value = tf.reduce_max(specs)
    normalized_spec = specs / max_value
    return normalized_spec, max_value

#get the number of classes from the number of folders in the audio dir
def get_n_classes(audio_path):
    root, dirs, files = next(os.walk(audio_path))
    n_classes = len(dirs)
    print(f'Found {n_classes} different classes in {audio_path}')
    return n_classes

#load the audio. Pad the audio if the file is shorter than the maximum architecture capacity
def load_audio(audio_path, sr, audio_size_samples):
    X_audio, _ = librosa.load(audio_path, sr = sr)
    if X_audio.size < audio_size_samples:
        padding = audio_size_samples - X_audio.size
        X_audio = np.pad(X_audio, (0, padding), mode = 'constant')
    elif (X_audio.size >= audio_size_samples):
        X_audio = X_audio[0:audio_size_samples]
    X_audio = X_audio.astype(np.float64)
    return X_audio

#save the label names for inference
def save_label_names(audio_path, save_folder):
    label_names = {}
    for i, folder in enumerate(next(os.walk(audio_path))[1]):
        label_names[i] = folder
    #save the dictionary to use it later with the standalone generator
    with open(os.path.join(save_folder, 'label_names.json'), 'w') as outfile:
        json.dump(label_names, outfile)
        
#create the dataset from the audio path folder
def create_dataset(audio_path, sample_rate, labels_saving_path, audio_size_samples):
    
    #save the label names in a dict
    save_label_names(audio_path, labels_saving_path)
    audio = []
    labels_names = []
    print('Processing audio and assigning labels')
    for folder in next(os.walk(audio_path))[1]:
        for wavfile in os.listdir(audio_path+folder):
            audio.append(load_audio(audio_path = f'{audio_path}{folder}/{wavfile}', sr = sample_rate, audio_size_samples = audio_size_samples))
            if len(audio) % 1000 == 0:
                print('Number of labels that have been assigned:', len(audio))
            labels_names.append(folder)
    audio_np = np.asarray(audio)
    audio_np = np.expand_dims(audio_np, axis = -1)
    labels = np.unique(labels_names, return_inverse=True)[1]
    labels_np = np.expand_dims(labels, axis = -1)

    # wave = tf.reshape(tf.cast(audio,tf.float32),(-1,16384))
    # specs = tfio.audio.spectrogram(wave, nfft=254, window=254, stride=64)
    # normalized_spec, max_value = normalize(specs)
    # log_spec = tf.math.log(tf.clip_by_value(t=normalized_spec, clip_value_min=tf.exp(-10.0), clip_value_max=float("inf")))
    # log_spec = log_spec/(-clipBelow/2)+1
    # specs = tf.reshape(log_spec, (-1, 256, 128, 1))
    # specs = np.asarray(specs)
    
    return audio_np, labels_np

#create folder with current date (to avoid overriding the synthesised audio/model when resuming the training)
def create_date_folder(checkpoints_path,name):
    if not os.path.exists(checkpoints_path):
        os.mkdir(checkpoints_path)
    date = datetime.now()
    day = date.strftime('%d-%m-%Y_')
    path = f'{checkpoints_path}{day}{str(date.hour)}_{name}'
    if not os.path.exists(path):
        os.mkdir(path)
    if not os.path.exists(f'{path}/synth_audio'):
        os.mkdir(f'{path}/synth_audio')     
    return path

#save the training arguments used to the checkpoints folder (it make it easier retrieve the hyperparameters afterwards)
def write_parameters(n_batches, batch_size, audio_path, checkpoints_path, path_to_weights, resume_training, override_saved_model, synth_frequency, 
                save_frequency, latent_dim, use_batch_norm, discriminator_learning_rate, generator_learning_rate,
                discriminator_extra_steps, phaseshuffle_samples):
    print(f'Saving the training parameters to disk in {checkpoints_path}/training_parameters.txt')
    arguments = open(f'{checkpoints_path}/training_parameters.txt', "w")
    arguments.write(f'n_batches = {n_batches}\n')
    arguments.write(f'batch_size = {batch_size}\n')
    arguments.write(f'audio_path = {audio_path}\n')
    arguments.write(f'checkpoints_path = {checkpoints_path}\n')
    arguments.write(f'path_to_weights = {path_to_weights}\n')
    arguments.write(f'resume_training = {resume_training}\n')
    arguments.write(f'override_saved_model = {override_saved_model}\n')
    arguments.write(f'synth_frequency = {synth_frequency}\n')
    arguments.write(f'save_frequency = {save_frequency}\n')
    arguments.write(f'latent_dim = {latent_dim}\n')
    arguments.write(f'use_batch_norm = {use_batch_norm}\n')
    arguments.write(f'discriminator_learning_rate = {discriminator_learning_rate}\n')
    arguments.write(f'generator_learning_rate = {generator_learning_rate}\n')
    arguments.write(f'discriminator_extra_steps = {discriminator_extra_steps}\n')
    arguments.write(f'phaseshuffle_samples = {phaseshuffle_samples}')
    arguments.close()