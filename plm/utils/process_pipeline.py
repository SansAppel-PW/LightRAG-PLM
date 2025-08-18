import subprocess
import shlex
import threading


class ProcessPipline:
    """ 安全进程管道执行器 """

    def __init__(self, commands, timeout=None, *args, **kwargs):
        self.commands = commands
        self.timeout = timeout
        self.processes = []
        self._timer = None

    def run(self):
        """ 执行管道 """
        result = None
        try:
            last_stdout = None
            for cmd in self.commands:
                proc = subprocess.Popen(
                    cmd,
                    stdin=last_stdout,
                    stdout=subprocess.PIPE if cmd != self.commands[-1] else None,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                self.processes.append(proc)

                # 关闭上一个进程的stdout（若当前进程非第一个进程）
                if last_stdout is not None:
                    last_stdout.close()

                last_stdout = proc.stdout.fileno() if proc.stdout else None

            # 设置超时
            if self.timeout:
                self._start_timeout_timer()

            # 收集所有错误输出
            outputs = []
            errors = []

            # 收集中间进程的错误输出
            for i, proc in enumerate(self.processes[:-1]):
                proc.wait()
                if proc.stderr:
                    errors.append(f"[命令 {i+1} 错误]: {proc.stderr.read()}")

            # 从最后一个进程收集输出
            last_proc = self.processes[-1]
            stdout, stderr = last_proc.communicate()
            outputs.append(stdout or "")
            errors.append(stderr or "")

            # 检查返回码
            for i, proc in enumerate(self.processes):
                if proc.returncode != 0:
                    cmd_str = "|".join(" ".join(shlex.quote(a) for a in c)
                                       for c in self.commands)
                    raise subprocess.CalledProcessError(
                        proc.returncode,
                        cmd_str,
                        f"命令 {i + 1} 失败：{self.commands[i]}",
                        stderr="\n".join(errors)
                    )
            result = ("\n".join(outputs), "\n".join(errors) if errors else "")
        except (subprocess.CalledProcessError, TimeoutError) as e:
            raise e
        finally:
            # 清理资源
            self._cancel_timeout()
            for proc in self.processes:
                if proc.poll() is None:
                    proc.kill()
                # 确保所有文件描述符关闭
                for stream in [proc.stdin, proc.stdout, proc.stderr]:
                    if stream and not stream.closed:
                        stream.close()
            return result if result else ("", "your pipeline has exceptions...")

    def _start_timeout_timer(self):
        """ 启动超时计时器 """

        def kill_processes():
            for proc in self.processes:
                if proc.poll is None:
                    proc.kill()

        self._timer = threading.Timer(self.timeout, kill_processes)
        self._timer.start()

    def _cancel_timeout(self):
        """ 取消超时计时器 """
        if self._timer:
            self._timer.cancel()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 确保所有进程终止
        for proc in self.processes:
            if proc.poll() is None:
                proc.terminate()
        self._cancel_timeout()


if __name__ == "__main__":
    pipeline = [
        ['find', '.', '-name', '*.py'],
        ['xargs', 'wc', '-l'],
        ['sort', '-n']
    ]
    with ProcessPipline(pipeline, timout=60) as pp:
        try:
            outputs, errors = pp.run()
            print("处理结果：\n", outputs)
        except subprocess.CalledProcessError as e:
            print(f"管道执行失败：{e}\n错误输出:\n{e.stderr}")
