import pandas as pd
from torch.utils.data import Dataset, DataLoader
from voicemd.data.dataloaders import TrainDataset, EvalDataset, PredictDataset


def load_metadata(args, hyper_params):
    metadata = pd.read_csv(hyper_params['metadata_fname'])
    metadata = metadata.set_index('uid')
    metadata = metadata[metadata["filename"].notna()]
    return metadata


def get_metadata_splits(args, hyper_params, split):

    metadata = load_metadata(args, hyper_params)

    if hyper_params['split_type'] == 'even_split':
        # Split male and female, shuffle them,
        # join them back and sample evenly from both
        # Splitting evenly should only be for debugging
        male_metadata = metadata[metadata['gender'] == 'M']
        female_metadata = metadata[metadata['gender'] == 'F']

        male_metadata_shuffle = male_metadata.sample(n=len(male_metadata), random_state=hyper_params['split_rand_state'])
        female_metadata_shuffle = female_metadata.sample(n=len(female_metadata), random_state=hyper_params['split_rand_state'])

        train_metadata = male_metadata_shuffle[0:75].append(female_metadata_shuffle[0:75])
        train_metadata = train_metadata.sample(n=len(train_metadata), random_state=hyper_params['split_rand_state'])

        valid_metadata = male_metadata_shuffle[75:100].append(female_metadata_shuffle[75:100])
        valid_metadata = valid_metadata.sample(n=len(valid_metadata), random_state=hyper_params['split_rand_state'])

        test_metadata = male_metadata_shuffle[100:].append(female_metadata_shuffle[100:])
        test_metadata = test_metadata.sample(n=len(test_metadata), random_state=hyper_params['split_rand_state'])

    elif hyper_params['split_type'] == 'rand_shuffle':
        shuffled_metadata = metadata.sample(n=len(metadata), random_state=hyper_params['split_rand_state'])

        train_percentage = 0.8
        val_percentage = 0.1
        # test_percentage = 0.1

        train_metadata = shuffled_metadata[0:round(len(shuffled_metadata) * train_percentage)]
        valid_metadata = shuffled_metadata[round(len(shuffled_metadata) * train_percentage):round(len(shuffled_metadata)*(train_percentage + val_percentage))]
        test_metadata = shuffled_metadata[round(len(shuffled_metadata) * (train_percentage + val_percentage)):]

    elif hyper_params['split_type'] == 'debug':
        shuffled_metadata = metadata.sample(n=len(metadata), random_state=hyper_params['split_rand_state'])
        train_metadata = shuffled_metadata.iloc[0:32]
        valid_metadata = shuffled_metadata.iloc[0:32]
        test_metadata = shuffled_metadata.iloc[0:32]


    elif hyper_params['split_type'] == 'shuffled_kfold':

        from sklearn.model_selection import KFold
        percent_train = 0.9

        shuffled_metadata = metadata.sample(n=len(metadata), random_state=hyper_params['split_rand_state'])
        kf = KFold(n_splits=hyper_params['n_splits'])
        for split_idx, (train_val_index, test_index) in enumerate(kf.split(shuffled_metadata)):

            if split == split_idx:
                break


        train_index = train_val_index[0:(round(len(train_val_index)*percent_train))]
        valid_index = train_val_index[(round(len(train_val_index)*percent_train)):]

        train_metadata = shuffled_metadata.iloc[train_index]
        valid_metadata = shuffled_metadata.iloc[valid_index]
        test_metadata = shuffled_metadata.iloc[test_index]

    else:
        raise NotImplementedError("split_type not defined")

    return train_metadata, valid_metadata, test_metadata


def get_loaders(args, hyper_params, train_metadata, valid_metadata, test_metadata):
    # TODO: Add splits for validation


    train_data = TrainDataset(
        train_metadata,
        voice_clips_dir=args.data,
        spec_type=hyper_params['spec_type'],
        window_len=hyper_params['window_len'],
        in_channels=hyper_params['in_channels'],
        preprocess=True,
        normalize=hyper_params['normalize_spectrums'],
    )

    train_loader = DataLoader(
        train_data, batch_size=hyper_params["batch_size"], shuffle=True
    )

    valid_loaders = []
    for val_idx in range(len(valid_metadata)):
        valid_data = EvalDataset(
            valid_metadata.iloc[[val_idx]],
            voice_clips_dir=args.data,
            spec_type=hyper_params['spec_type'],
            window_len=hyper_params['window_len'],
            in_channels=hyper_params['in_channels'],
            preprocess=True,
            normalize=hyper_params['normalize_spectrums'],
            dev_step_size=hyper_params['dev_step_size']
        )
        valid_loaders.append(DataLoader(
                valid_data, batch_size=hyper_params["batch_size"], shuffle=False
            )
        )

    test_loaders = []
    for idx in range(len(test_metadata)):
        test_data = EvalDataset(
            test_metadata.iloc[[idx]],
            voice_clips_dir=args.data,
            spec_type=hyper_params['spec_type'],
            window_len=hyper_params['window_len'],
            in_channels=hyper_params['in_channels'],
            preprocess=True,
            normalize=hyper_params['normalize_spectrums'],
        )

        test_loader = DataLoader(
            test_data, batch_size=hyper_params["batch_size"], shuffle=False
        )

        test_loaders.append(test_loader)

    return train_loader, valid_loaders, test_loaders


def make_predict_dataloader(sound_filename, hyper_params):
    '''Useful for prediction on single file'''

    predict_dataset = PredictDataset(
            sound_filename=sound_filename,
            spec_type=hyper_params['spec_type'],
            window_len=hyper_params['window_len'],
            in_channels=hyper_params['in_channels'],
            preprocess=True,
            normalize=hyper_params['normalize_spectrums'],
        )

    predict_dataloader = DataLoader(
         predict_dataset, batch_size=hyper_params["batch_size"], shuffle=False
        )

    return predict_dataloader
