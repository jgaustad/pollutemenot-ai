## Create a security group and open ports for ssh and jupyter server:
```
aws ec2 create-security-group --group-name capstone1 --description "capstone group1"
aws ec2 authorize-security-group-ingress --group-id  sg-082657d635fcb99a6 --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id  sg-082657d635fcb99a6 --protocol tcp --port 8888 --cidr 0.0.0.0/0
```

## Get a .pem key for ssh and scp and save into a .pem file be sure to protect this file and not upload to git
```
aws ec2 create-key-pair --key-name capstone1key --query 'KeyMaterial' --output text > capstone1key.pem
chmod 400 *.pem file
```

## Check the spot prices for p2.xlarge ($0.27/hr) at this time.
```
aws --region=us-east-2 ec2 describe-spot-price-history --instance-types p2.xlarge --start-time=$(date +%s) --product-descriptions="Linux/UNIX" --query 'SpotPriceHistory[*].{az:AvailabilityZone, price:SpotPrice}' 
```

## Create a spot-options.json for max price you are willing to pay
```
{
  "MarketType": "spot",
  "SpotOptions": {
    "MaxPrice": "1.50",
    "SpotInstanceType": "one-time"
  }
}
```

## Spin up VM, replace the sg-XXXX... with your security group id
```
aws ec2 run-instances --image-id ami-09f77b37a0d32243a --instance-type p2.xlarge --security-group-ids sg-082657d635fcb99a6 --associate-public-ip-address --instance-market-options file://spot-options.json --key-name capstone1key
```

## Get the public DNS for ssh and jupyter purposes this can also be found on the web console:
```
aws ec2 describe-instances | grep ec2 
# ubuntu@ec2-3-15-2-241.us-east-2.compute.amazonaws.com

aws ec2 describe-instances | grep PublicIp
# 54.194.227.21
```

## SSH into the console, replace the @.... with your public dns
```
ssh -i "capstone1key.pem" ubuntu@ec2-3-15-2-241.us-east-2.compute.amazonaws.com
```

## Now in the aws VM console, Clone the pollutemenot-ai git
```
git clone https://github.com/jgaustad/pollutemenot-ai.git
```

## Mounting an EFS across accounts
Uh oh.   Not sure how to do this effectively.   Might need to read up here: https://docs.aws.amazon.com/efs/latest/ug/manage-fs-access-vpc-peering.html

## Build the docker image from docker_p2.dockerfile by running shell script:
```
./pollutemenot-ai/build_docker.sh
```

## Launch docker with mounted volumes ( may need to edit command if mounts are different):
```
./pollutemenot-ai/start_docker.sh
```

## Get the name of the docker instance, this example is fervid_flower
```
docker ps -a
docker attach fervid_flower
``` 

## Launch jupyter
```
./pmn-ai/start_jupyter.sh
```

## In browser use the public IP and port 8888 to connect to the jupyter lab
Navigate to the proper IP address, something like this ```54.194.227.21:8888```

## Enjoy the jupyter lab environment



