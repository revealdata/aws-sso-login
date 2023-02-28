import sys
import os
import re
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import QSize, Qt, QByteArray, QProcess
from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QButtonGroup ,QGridLayout, QCheckBox, QStatusBar, QLineEdit, QTextEdit, QLabel
from lib.icon import ICON
from lib.classes import Initialize

QApp = QApplication(sys.argv)
Icon = ICON("aws_identity_center.png")

class QCheckBoxOptions(QCheckBox):
    def __init__(self, name, metadata, button, options):
        super().__init__()
        self.name = name
        self.metadata = metadata
        self.button = button
        self.options = options
        self.setText(self.metadata.label)
        self.setChecked(self.metadata.value)
        self.setToolTip(self.metadata.help)
        self.stateChanged.connect(self.checkbox_changed)

    def checkbox_changed(self, state):
        """ Process the checkbox clicks. """
        any_checked = False
        for checkbox in self.options:
            value = self.options[checkbox].isChecked()
            any_checked = value or any_checked
            self.options[checkbox].value = value

        # Set the start button to enabled if any checkbox is checked.
        self.button.setEnabled(any_checked)

    
class QLineConfig(QLineEdit):
    def __init__(self, name, metadata, button=None, options=None, parent=None):
        super().__init__()
        self.name = name
        self.value = metadata.value
        self.button = button
        self.metadata = metadata
        self.options = options
        self.parent = parent
        self.setText(self.value)
        self.setToolTip(self.metadata.help)
        self.setPlaceholderText(self.metadata.help)
        # self.editingFinished.connect(self.config_validate)
        self.textChanged[str].connect(self.__config_validate__)
        self.__config_validate__(value=str(self.value))
        self.__cmd_validate__()

    def __cmd_validate__(self):
        """ Validate the command line arguments. """
        if "version" in self.metadata.verification and self.metadata.value:
            args = self.metadata.verification["version"]["args"].split(" ")
            self.parent.init_process(capture=True)
            self.parent.process.start(self.metadata.value, args)
            self.parent.process.waitForFinished()
            version = re.match(self.metadata.verification["version"]["regex"], self.parent.capture)
            if not version or not self.parent.process.exitCode() == 0:
                self.__toggle_checkbox__(False)
        
        if "alive" in self.metadata.verification and self.metadata.value:
            args = self.metadata.verification["alive"]["args"].split(" ")
            self.parent.init_process(capture=True)
            self.parent.process.start(self.metadata.value, args)
            self.parent.process.waitForFinished()
            if not self.parent.process.exitCode() == 0:
                self.__toggle_checkbox__(False)
    
    def __config_validate__(self, value=None):
        self.__toggle_checkbox__(os.path.isfile(value))

    def __toggle_checkbox__(self, enabled=True):
        if enabled:
            self.setStyleSheet("background-color: #000000; color: #FFFFFF;")
            if self.button and self.metadata.stop_run:
                self.button.setEnabled(True)
            for checkbox in self.metadata.stop_options:
                self.options[checkbox].setEnabled(True)
                self.options[checkbox].setChecked(True)
        else:
            self.setStyleSheet("background-color: #FF0000; color: #000000;")
            if self.button and self.metadata.stop_run:
                self.button.setEnabled(False)
            for checkbox in self.metadata.stop_options:
                self.options[checkbox].setEnabled(False)
                self.options[checkbox].setChecked(False)


class MainWindow(QMainWindow):
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs
        self.options = {}
        self.config = {}
        self.message_prefix = None
        self.message_postfix = None
        self.capture = None
        self.app = self.kwargs["app"]
        self.args = Initialize(self.kwargs["arguments"])
        self.layout = QGridLayout()

        pixmap = QtGui.QPixmap()
        if Icon.base64:
            pixmap.loadFromData(QByteArray.fromBase64(Icon.base64))
            QApp.setWindowIcon(QtGui.QIcon(QtGui.QIcon(pixmap)))

        # Set the central widget of the Window.
        widget = QWidget(self)
        self.setCentralWidget(widget)

        # self.setFixedSize(QSize(600, 800))
        self.setMinimumSize(QSize(740, 800))
        self.setWindowTitle(f"{self.app['description']}")

        optionsgroup = QGroupBox("Login Options")
        optionsgroup.setFixedHeight(90)
        self.options_layout = QHBoxLayout()
        optionsgroup.setLayout(self.options_layout)
        
        configgroup = QGroupBox("Configuration")
        self.config_layout = QHBoxLayout()
        configgroup.setLayout(self.config_layout)

        output_label = QLabel("Output")
        output_layout = QVBoxLayout()
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFontPointSize(16)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output)

        buttons_layout = QHBoxLayout()
        self.buttongroup = QButtonGroup()
        self.buttongroup.buttonClicked.connect(self.button_clicked)
        self.button_cancel = QPushButton("Exit")
        self.button_cancel.setFixedHeight(40)
        self.button_start = QPushButton("Start")
        self.button_start.setFixedHeight(40)
        self.buttongroup.addButton(self.button_cancel, 0)
        self.buttongroup.addButton(self.button_start, 1)
        self.buttongroup.setExclusive(True)
        
        buttons_layout.addWidget(self.buttongroup.button(0))
        buttons_layout.addWidget(self.buttongroup.button(1))

        self.layout.addWidget(optionsgroup, 0, 0,1,2)
        self.layout.addWidget(configgroup, 1, 0,1,2)
        self.layout.addLayout(output_layout, 2, 0, 1, 2)
        self.layout.addLayout(buttons_layout, 3, 0, 1, 2)
        widget.setLayout(self.layout)

        self.statusbar = QStatusBar()
        self.statusbar.showMessage(f"{self.app['name']} v{self.app['version']}")
        self.statusbar.setToolTip(f"Author: {self.app['author']}")
        self.statusbar.layout().setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setStatusBar(self.statusbar)

        self.__load_ui_options__()
        self.__load_ui_config__()
        self.__show_messages__()

    def __load_ui_options__(self):
        for key, meta in self.args.arguments["options"].items():
            self.options[key] = QCheckBoxOptions(
                name=key,
                metadata=meta,
                button=self.button_start,
                options=self.options,
            )
            self.options[key].setToolTip(meta.help)
            if not meta.enabled:
                self.options[key].setEnabled(False)
                self.options[key].setChecked(False)
            self.options[key].stateChanged.connect(self.checkbox_changed)
            
            self.options_layout.addWidget(self.options[key])

    def __load_ui_config__(self):
        for key, meta in self.args.arguments["cmd"].items():
            self.config[key] = QLineConfig(
                name=key,
                metadata=meta,
                button=self.button_start,
                options=self.options,
                parent=self
            )
            self.config_layout.addWidget(QLabel(f"{key}:"))
            self.config_layout.addWidget(self.config[key])
            

    def button_clicked(self, button):
        """ Process the button clicks. """
        if button.text() == "Exit":
            QApp.quit()
        elif button.text() == "Start":
            button.setEnabled(False)
            self.run()

    def checkbox_changed(self, state):
        """ Process the checkbox clicks. """
        any_checked = False
        for checkbox in self.options:
            value = self.options[checkbox].isChecked()
            any_checked = value or any_checked
            self.args.arguments["options"][checkbox].value = value

        # Set the start button to enabled if any checkbox is checked.
        self.buttongroup.button(1).setEnabled(any_checked)
    
    def __show_messages__(self):
        for section in self.args.arguments:
            for arg in self.args.arguments[section]:
                if not len(self.args.arguments[section][arg].errors) == 0:
                    for error in self.args.arguments[section][arg].errors:
                        self.message(error)


    def run(self):
        self.output.clear()
        self.message("Starting Login and Authorization Process...")
        
        # SSO Login
        if self.options["do_login"].isChecked():
            self.message("<strong>Begin AWS SSO Login. Please wait...</strong>")
            for name, profile in self.args.profiles.items():
                if hasattr(profile, "sso_start_url") and profile.sso_start_url:
                    self.init_process()
                    self.message_prefix = f"- [{name}]: "
                    self.call_program(f"{self.args.arguments['cmd']['awscli'].value}", ["--profile", f"{profile.name}", "--region", f"{profile.region}","sso", "login", '--no-cli-pager'])
                    self.process.waitForFinished()
                    self.message_prefix = None

            self.message("AWS SSO Login Completed.<br/>")

        # ECR Login
        if self.options["do_ecr"].isChecked():
            self.message("<strong>Begin ECR Login. Please wait...</strong>")
            for name, profile in self.args.profiles.items():
                if hasattr(profile, "sso_account_id") and profile.sso_account_id:
                    self.init_process(True)
                    self.message_prefix = f"- [{name}]: "
                    self.call_program(f"{self.args.arguments['cmd']['awscli'].value}", [
                        "--profile", f"{profile.name}",
                        "ecr", "get-login-password",
                        "--region", f"{profile.region}",
                        "--no-cli-pager"
                    ])
                    self.process.waitForFinished()
                    if self.capture:
                        profile.ecr_password = self.capture
                        self.capture = None
                    if profile.ecr_password:
                        self.call_program(
                            f"{self.args.arguments['cmd']['docker'].value}", [
                            "login",
                            "--username",
                            "AWS",
                            "--password", f"{profile.ecr_password}", 
                            f"{profile.sso_account_id}.dkr.ecr.{profile.region}.amazonaws.com"
                            ]
                        )
                        self.process.waitForFinished()
                        self.message_prefix = None
                    else:
                        self.message("Failed to get ECR password. Check AWS CLI configuration.")
            self.message("AWS ECR Login Completed.<br/>")

        # Kubectl Login
        if self.options["do_eks"].isChecked():
            self.message("<strong>Begin kubectl Authorization. Please wait...</strong>")
            for name, kubeconfig in self.args.kube_configs.items():
                if kubeconfig.aws_profile and kubeconfig.enable:
                    
                    # self.message(f"\n<br/><strong>[Kubeconfig: {name}]</strong>")
                    self.message_prefix = f"- [{name}]: "
                    self.init_process()

                    # Set the AWS region variable
                    if hasattr(kubeconfig, "aws_region"):
                        region = kubeconfig.aws_region
                    else:
                        region = kubeconfig.aws_profile.region
                        print(type(kubeconfig.aws_profile))

                    args = [
                            "--profile", f"{kubeconfig.aws_profile.name}",
                            "eks", "update-kubeconfig",
                            "--name", f"{kubeconfig.eks_cluster}",
                            "--region", f"{region}",
                            "--alias", f"{kubeconfig.context}",
                            "--output", "json"
                        ]
                    # Add a role if specified
                    if hasattr(kubeconfig, "role"):
                        args.extend(["--role-arn", f"arn:aws:iam::{kubeconfig.aws_profile.sso_account_id}:role/{kubeconfig.eks_cluster}-{kubeconfig.role}"])
                    # Add a specific kube config file if specified
                    if hasattr(kubeconfig, "kube_config"):
                        args.extend(["--kubeconfig", f"{kubeconfig.kube_config}"])

                    self.call_program(f"{self.args.arguments['cmd']['awscli'].value}", args)
                    self.process.waitForFinished()
                    self.message_prefix = None
            self.message("AWS EKS Authorization Completed.<br/>")

        self.button_start.setEnabled(True)

    def init_process(self, capture=False):
        self.process = QtCore.QProcess(self)
        # self.process.readyRead.connect(self.data_ready)
        if capture:
            self.process.readyReadStandardOutput.connect(self.handle_stdout_capture)
        else:
            self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        self.process.started.connect(self.process_started)

    def data_ready(self):
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        # Decode the QByteArray
        cursor.insertText(
            str(self.process.readAll().data().decode()))
        self.output.ensureCursorVisible()

    def call_program(self, command, args=[]):
        # run the process
        # `start` takes the exec and a list of arguments
        self.process.start(command, args)

    def message(self, message, prefix="", postfix=""):
        if self.message_prefix:
            prefix = self.message_prefix
        if self.message_postfix:
            postfix = self.message_postfix

        self.output.append(f"{prefix}{message.strip()}{postfix}")
        QApp.processEvents()

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.message(stderr)

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.message(stdout)
    
    def handle_stdout_capture(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.capture = stdout
        return stdout

    def process_started(self):
        pass

    def process_finished(self):
        if self.process.exitCode() != 0:
            self.message(f"Process Failed. Reason: {self.process.errorString()}")
        self.process.close()
