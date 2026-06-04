#!/usr/bin/env python3
import aws_cdk as cdk

from stacks.bada_stack import BadaStack

app = cdk.App()
BadaStack(app, "BadaDev", env=cdk.Environment(region="ap-northeast-2"))
app.synth()
