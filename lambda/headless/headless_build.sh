# aws lambda create-function \
#     --function-name headless-test \
#     --zip-file fileb://./headless-test.zip \
#     --role $AWS_LAMBDA_ROLE \
#     --handler lambda_handler.handler \
#     --runtime nodejs6.10 \
#     --timeout 300 \
#     --memory-size 1536

aws lambda update-function-code \
    --function-name headless-test \
    --zip-file fileb://./headless-test.zip \
