from typing import final
from typing import Any
from typing import List
from typing import Final
from typing import Dict

from abc import ABC
from abc import abstractmethod


class GradFunc(ABC):
    @staticmethod
    @abstractmethod
    def forward(ctx: Dict[str, Any], *args: List[Any], **kwargs: Dict[str, Any]) -> Any:
        raise NotImplementedError("Forward method not implemented!")

    @staticmethod
    @abstractmethod
    def backward(
        ctx: Dict[str, Any], *args: List[Any], **kwargs: Dict[str, Any]
    ) -> Any:
        raise NotImplementedError("Backward method not implemented!")


@final
class GradT(GradFunc):
    @staticmethod
    def forward(ctx: Dict[str, Any], x: Any) -> Any:
        return x.t()

    @staticmethod
    def backward(ctx: Dict[str, Any], grad: Any) -> Any:
        return grad.t()


@final
class GradAdd(GradFunc):
    @staticmethod
    def forward(ctx: Dict[str, Any], x: Any, y: Any) -> Any:
        assert x.shape == y.shape

        return x + y

    @staticmethod
    def backward(ctx: Dict[str, Any], grad: Any) -> Any:
        return grad, grad.clone()


@final
class GradSum(GradFunc):
    @staticmethod
    def forward(ctx: Dict[str, Any], x: Any) -> Any:
        ctx["x_shape"] = x.shape
        total_sum = x.sum()
        return total_sum

    @staticmethod
    def backward(ctx: Dict[str, Any], grad: Any) -> Any:
        x_shape = ctx["x_shape"]
        return grad * torch.ones(shape=x_shape)


@final
class GradSigmoid(GradFunc):
    @staticmethod
    def forward(ctx: Dict[str, Any], x: Any) -> Any:

        grad = x.sigmoid()
        ctx["probs"] = grad
        return grad

    @staticmethod
    def backward(ctx: Dict[str, Any], grad: Any) -> Any:
        probs = ctx["probs"]
        return grad * probs * (1 - probs)


@final
class GradSub(GradFunc):
    @staticmethod
    def forward(ctx: Dict[str, Any], x: Any, y: Any) -> Any:
        assert x.shape == b.shape
        return x - y

    @staticmethod
    def backward(ctx: Dict[str, Any], grad: Any) -> Any:
        return grad, grad.clone()


@final
class GradMul(GradFunc):
    @staticmethod
    def forward(ctx: Dict[str, Any], x: Any, y: Any) -> Any:
        # TODO: Tackle the broadcast step
        # Make sure we do not broadcast because we would need to deal with this
        # in the backward
        assert x.shape == y.shape
        ctx["x"] = x
        ctx["y"] = y
        return x * y

    @staticmethod
    def backward(ctx: Dict[str, Any], grad: Any) -> Any:
        x, y = ctx["x"], ctx["y"]
        return grad * y, grad * x


def forward(_self, grad_fn, *args: List[Any], **kwargs: Dict[str, Any]) -> "MPCTensor":
    # TODO: Fix this import
    from ..mpc_tensor import MPCTensor

    mpc_tensor_params = [_self] + [arg for arg in args if isinstance(arg, MPCTensor)]
    requires_grad = any(mpc_tensor.requires_grad for mpc_tensor in mpc_tensor_params)

    MPCTensor.AUTOGRAD_IS_ON = False
    res = grad_fn.forward(_self.ctx, _self, *args, **kwargs)
    MPCTensor.AUTOGRAD_IS_ON = True

    res.requires_grad = requires_grad
    res.grad_fn = grad_fn
    res.ctx = _self.ctx.copy()
    res.parents = mpc_tensor_params
    for mpc_tensor in mpc_tensor_params:
        mpc_tensor.nr_out_edges += 1
    return res


GRAD_FUNCS: Final[Dict[str, GradFunc]] = {
    "t": GradT,
    "mul": GradMul,
    "sub": GradSub,
    "add": GradAdd,
    "sum": GradSum,
    "sigmoid": GradSigmoid,
}
