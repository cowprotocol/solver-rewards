FROM public.ecr.aws/lambda/nodejs:18 as builder
WORKDIR /usr/app
COPY ./  ./

RUN npm install
RUN npm run build

FROM public.ecr.aws/lambda/nodejs:18
WORKDIR ${LAMBDA_TASK_ROOT}
COPY --from=builder /usr/app/node_modules/ ./node_modules
COPY --from=builder /usr/app/out/ ./
CMD ["lambda.handler"]
