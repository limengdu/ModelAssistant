from typing import Dict, List, Sequence, Union

import onnx
import torch
from mmengine.evaluator.evaluator import Evaluator
from mmengine.runner import Runner
from mmengine.runner.loops import BaseLoop, EpochBasedTrainLoop
from torch.utils.data import DataLoader

from sscma.registry import LOOPS


@LOOPS.register_module()
class GetEpochBasedTrainLoop(EpochBasedTrainLoop):
    def run_iter(self, idx, data_batch: Sequence[dict]) -> None:
        """Iterate one min-batch.

        Args:
            data_batch (Sequence[dict]): Batch of data from dataloader.
        """
        self.data_batch = data_batch
        self.runner.call_hook('before_train_iter', batch_idx=idx, data_batch=self.data_batch)
        # Enable gradient accumulation mode and avoid unnecessary gradient
        # synchronization during gradient accumulation process.
        # outputs should be a dict of loss.
        self.outputs = self.runner.model.train_step(self.data_batch, optim_wrapper=self.runner.optim_wrapper)

        self.runner.call_hook('after_train_iter', batch_idx=idx, data_batch=self.data_batch, outputs=self.outputs)
        self._iter += 1


@LOOPS.register_module()
class EdgeTestLoop(BaseLoop):
    def __init__(
        self,
        runner: Runner,
        dataloader: Union[DataLoader, Dict],
        evaluator: Union[Evaluator, Dict, List],
        fp16: bool = False,
    ):
        super().__init__(runner, dataloader)


@LOOPS.register_module()
class EdgeTestRunner:
    def __init__(
        self,
        model: Union[str, List],
    ) -> None:
        if isinstance(model, list):
            try:
                import ncnn
            except ImportError:
                raise ImportError(
                    'You have not installed ncnn yet, please execute the "pip install ncnn" command to install and run again'
                )
            net = ncnn.Net()
            for p in model:
                if p.endswith('param'):
                    param = p
                if p.endswith('bin'):
                    bin = p
            net.load_param(param)
            net.load_model(bin)
            # net.opt.use_vulkan_compute = True
            self.engine = 'ncnn'
        elif model.endswith('onnx'):
            try:
                import onnxruntime
            except ImportError:
                raise ImportError(
                    'You have not installed onnxruntime yet, please execute the "pip install onnxruntime" command to install and run again'
                )
            try:
                net = onnx.load(model)
                onnx.checker.check_model(net)
            except ValueError:
                raise ValueError('onnx file have error,please check your onnx export code!')
            providers = (
                ['CUDAExecutionProvider', 'CPUExecutionProvider']
                if torch.cuda.is_available()
                else ['CPUExecutionProvider']
            )
            net = onnxruntime.InferenceSession(model, providers=providers)
            self.engine = 'onnx'
        elif model.endswith('tflite'):
            try:
                import tensorflow as tf
            except ImportError:
                raise ImportError(
                    'You have not installed tensorflow yet, please execute the "pip install tensorflow" command to install and run again'
                )
            inter = tf.lite.Interpreter
            net = inter(model)
            net.allocate_tensors()
            self.engine = 'tf'
        else:
            raise 'model file input error'
        self.inter = net

    def show(self):
        pass

    def metric(self):
        pass

    def test(self):
        pass
