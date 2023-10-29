import aws_cdk as core
import aws_cdk.assertions as assertions

from infrastructure.infrastructure_stack import InfrastructureStack

# example tests. To run these tests, uncomment this file along with the example
# resource in infrastructure/infrastructure_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = InfrastructureStack(app, "infrastructure")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
