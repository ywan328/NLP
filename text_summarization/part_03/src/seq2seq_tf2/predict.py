# -*- coding:utf-8 -*-
# Created by LuoJie at 12/12/19
import os
import tensorflow as tf
from src.seq2seq_tf2.seq2seq_batcher import beam_test_batch_generator
from src.seq2seq_tf2.seq2seq_model import Seq2Seq
from src.seq2seq_tf2.predict_helper import beam_decode, greedy_decode
from src.utils.config import seq2seq_checkpoint_dir, test_x_path, test_y_path, test_seg_path
from src.utils.gpu_utils import config_gpu
from src.utils.params_utils import get_params
from src.build_data.utils import load_dataset
from src.utils.wv_loader import Vocab
import pandas as pd
from rouge import Rouge
import json


def love(params):
    assert params["mode"].lower() in ["test", "eval"], "change training mode to 'test' or 'eval'"
    assert params["beam_size"] == params["batch_size"], "Beam size must be equal to batch_size, change the params"
    # GPU资源配置
    config_gpu()

    print("Creating the vocab ...")
    vocab = Vocab(params["vocab_path"], params["vocab_size"])
    params['vocab_size'] = vocab.count

    print("Building the model ...")
    model = Seq2Seq(params, vocab)

    print("Creating the checkpoint manager")
    checkpoint = tf.train.Checkpoint(Seq2Seq=model)
    checkpoint_manager = tf.train.CheckpointManager(checkpoint, seq2seq_checkpoint_dir, max_to_keep=5)
    checkpoint.restore(checkpoint_manager.latest_checkpoint)
    # checkpoint.restore('../../data/checkpoints/training_checkpoints_seq2seq/ckpt-6')
    if checkpoint_manager.latest_checkpoint:
        print("Restored from {}".format(checkpoint_manager.latest_checkpoint))
    else:
        print("Initializing from scratch.")
    print("Model restored")

    if params['greedy_decode']:
        print('Using greedy search to decoding ...')
        predict_result(model, params, vocab)
    else:
        print('Using beam search to decoding ...')
        b = beam_test_batch_generator(params["beam_size"])
        results = []
        for batch in b:
            best_hyp = beam_decode(model, batch, vocab, params)
            results.append(best_hyp.abstract)
        get_rouge(results)
        print('save result to :{}'.format(params['result_save_path']))


def predict_result(model, params, vocab):
    test_X, _ = load_dataset(test_x_path, test_y_path,
                             params['max_enc_len'], params['max_dec_len'])
    # 预测结果
    results = greedy_decode(model, test_X, params['batch_size'], vocab, params)
    # 保存结果
    get_rouge(results)


def get_rouge(results):
    # 读取结果
    seg_test_report = pd.read_csv(test_seg_path, header=None).iloc[:, 5].tolist()
    seg_test_report = [' '.join(str(token) for token in str(line).split()) for line in seg_test_report]
    rouge_scores = Rouge().get_scores(results, seg_test_report, avg=True)
    print_rouge = json.dumps(rouge_scores, indent=2)
    with open(os.path.join(os.path.dirname(test_seg_path), 'results.csv'), 'w', encoding='utf8') as f:
        json.dump(list(zip(results, seg_test_report)), f, indent=2, ensure_ascii=False)
    print('*' * 8 + ' rouge score ' + '*' * 8)
    print(print_rouge)


if __name__ == '__main__':
    # 获得参数
    params = get_params()
    params['greedy_decode'] = False
    params['beam_size'] = params['batch_size'] = 4
    # 获得参数
    love(params)
