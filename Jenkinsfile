
        stage('Test AWS EC2 SSH Connection') {
            environment {
                EC2_HOST = '13.203.205.80'
            }
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'ec2-ssh-key',
                        keyFileVariable: 'SSH_KEY',
                        usernameVariable: 'SSH_USER'
                    )
                ]) {
                    script {
                        if (isUnix()) {
                            sh '''
                                ssh -o StrictHostKeyChecking=accept-new \
                                    -i "$SSH_KEY" \
                                    "$SSH_USER@$EC2_HOST" \
                                    "echo VisionPlay-EC2-SSH-SUCCESS"
                            '''
                        } else {
                            bat '''
                                ssh -o StrictHostKeyChecking=accept-new -i "%SSH_KEY%" %SSH_USER%@%EC2_HOST% "echo VisionPlay-EC2-SSH-SUCCESS"
                            '''
                        }
                    }
                }
            }
        }
