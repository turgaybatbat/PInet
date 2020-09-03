from __future__ import print_function
import torch
import torch.nn as nn
import torch.nn.parallel
import torch.utils.data
from torch.autograd import Variable
import numpy as np
import torch.nn.functional as F


class STN3d(nn.Module):
    def __init__(self):
        super(STN3d, self).__init__()
        self.conv1 = torch.nn.Conv1d(3, 64, 1)
        self.conv2 = torch.nn.Conv1d(64, 128, 1)
        self.conv3 = torch.nn.Conv1d(128, 1024, 1)
        self.fc1 = nn.Linear(1024, 512)
        self.fc2 = nn.Linear(512, 256)
        self.fc3 = nn.Linear(256, 9)
        self.relu = nn.ReLU()

        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(1024)
        self.bn4 = nn.BatchNorm1d(512)
        self.bn5 = nn.BatchNorm1d(256)
        #
        # self.bn1 = nn.InstanceNorm1d(64)
        # self.bn2 = nn.InstanceNorm1d(128)
        # self.bn3 = nn.InstanceNorm1d(1024)
        # self.bn4 = nn.InstanceNorm1d(512)
        # self.bn5 = nn.InstanceNorm1d(256)


    def forward(self, x):
        batchsize = x.size()[0]
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = torch.max(x, 2, keepdim=True)[0]
        x = x.view(-1, 1024)

        x = F.relu(self.bn4(self.fc1(x)))
        x = F.relu(self.bn5(self.fc2(x)))
        x = self.fc3(x)
        # print(x.size())

        iden = Variable(torch.from_numpy(np.array([1,0,0,0,1,0,0,0,1]).astype(np.float32))).view(1,9).repeat(batchsize,1)
        # print(iden)
        if x.is_cuda:
            iden = iden.cuda()
        x = x + iden
        x = x.view(-1, 3, 3)
        return x


class STNkd(nn.Module):
    def __init__(self, k=64):
        super(STNkd, self).__init__()
        self.conv1 = torch.nn.Conv1d(k, 64, 1)
        self.conv2 = torch.nn.Conv1d(64, 128, 1)
        self.conv3 = torch.nn.Conv1d(128, 1024, 1)
        self.fc1 = nn.Linear(1024, 512)
        self.fc2 = nn.Linear(512, 256)
        self.fc3 = nn.Linear(256, k*k)
        self.relu = nn.ReLU()

        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(1024)
        self.bn4 = nn.BatchNorm1d(512)
        self.bn5 = nn.BatchNorm1d(256)
        #
        # self.bn1 = nn.InstanceNorm1d(64)
        # self.bn2 = nn.InstanceNorm1d(128)
        # self.bn3 = nn.InstanceNorm1d(1024)
        # self.bn4 = nn.InstanceNorm1d(512)
        # self.bn5 = nn.InstanceNorm1d(256)

        self.k = k

    def forward(self, x):
        batchsize = x.size()[0]
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = torch.max(x, 2, keepdim=True)[0]
        x = x.view(-1, 1024)

        x = F.relu(self.bn4(self.fc1(x)))
        x = F.relu(self.bn5(self.fc2(x)))
        x = self.fc3(x)

        iden = Variable(torch.from_numpy(np.eye(self.k).flatten().astype(np.float32))).view(1,self.k*self.k).repeat(batchsize,1)
        if x.is_cuda:
            iden = iden.cuda()
        x = x + iden
        x = x.view(-1, self.k, self.k)
        return x

class PointNetfeat(nn.Module):
    def __init__(self, global_feat = True, feature_transform = False):
        super(PointNetfeat, self).__init__()
        self.stn = STN3d()
        self.conv1 = torch.nn.Conv1d(3, 64, 1)
        self.conv2 = torch.nn.Conv1d(64, 128, 1)
        self.conv3 = torch.nn.Conv1d(128, 1024, 1)
        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(1024)
        self.global_feat = global_feat
        self.feature_transform = feature_transform
        if self.feature_transform:
            self.fstn = STNkd(k=64)

    def forward(self, x):
        n_pts = x.size()[2]
        trans = self.stn(x)
        x = x.transpose(2, 1)
        x = torch.bmm(x, trans)
        x = x.transpose(2, 1)
        x = F.relu(self.bn1(self.conv1(x)))

        if self.feature_transform:
            trans_feat = self.fstn(x)
            x = x.transpose(2,1)
            x = torch.bmm(x, trans_feat)
            x = x.transpose(2,1)
        else:
            trans_feat = None

        pointfeat = x
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.bn3(self.conv3(x))
        x = torch.max(x, 2, keepdim=True)[0]
        x = x.view(-1, 1024)
        if self.global_feat:
            x = x.view(-1, 1024, 1)
            return x, pointfeat, trans, trans_feat
        else:
            x = x.view(-1, 1024, 1).repeat(1, 1, n_pts)
            # return torch.cat([x, pointfeat], 1), trans, trans_feat
            return x, pointfeat, trans, trans_feat

class PointNetfeat2(nn.Module):
    def __init__(self, global_feat = True, feature_transform = False):
        super(PointNetfeat2, self).__init__()
        # self.stn = STN3d()
        self.stn=STNkd(k=5)
        # self.conv1 = torch.nn.Conv1d(3, 64, 1)
        self.conv1 = torch.nn.Conv1d(5, 64, 1)
        self.conv2 = torch.nn.Conv1d(64, 128, 1)
        self.conv3 = torch.nn.Conv1d(128, 1024, 1)
        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(1024)
        self.global_feat = global_feat
        self.feature_transform = feature_transform
        if self.feature_transform:
            self.fstn = STNkd(k=64)

    def forward(self, x):
        n_pts = x.size()[2]
        trans = self.stn(x)
        x = x.transpose(2, 1)
        x = torch.bmm(x, trans)
        x = x.transpose(2, 1)
        x = F.relu(self.bn1(self.conv1(x)))

        if self.feature_transform:
            trans_feat = self.fstn(x)
            x = x.transpose(2,1)
            x = torch.bmm(x, trans_feat)
            x = x.transpose(2,1)
        else:
            trans_feat = None

        pointfeat = x
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.bn3(self.conv3(x))
        x = torch.max(x, 2, keepdim=True)[0]
        x = x.view(-1, 1024)
        if self.global_feat:
            x = x.view(-1, 1024, 1)
            return x, pointfeat, trans, trans_feat
        else:
            x = x.view(-1, 1024, 1).repeat(1, 1, n_pts)
            # return torch.cat([x, pointfeat], 1), trans, trans_feat
            return x, pointfeat, trans, trans_feat

class PointNetfeat3(nn.Module):
    def __init__(self, d=4,global_feat = True, feature_transform = False):
        super(PointNetfeat3, self).__init__()
        self.stn = STN3d()
        # self.stn=STNkd(k=d)
        self.conv1 = torch.nn.Conv1d(3, 64, 1)
        # self.conv1 = torch.nn.Conv1d(d, 64, 1)
        self.conv2 = torch.nn.Conv1d(64, 128, 1)
        self.conv3 = torch.nn.Conv1d(128, 1024, 1)
        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(1024)
        self.global_feat = global_feat
        self.feature_transform = feature_transform
        if self.feature_transform:
            self.fstn = STNkd(k=64)

    def forward(self, x):
        n_pts = x.size()[2]
        trans = self.stn(x)
        x = x.transpose(2, 1)
        x = torch.bmm(x, trans)
        x = x.transpose(2, 1)
        x = F.relu(self.bn1(self.conv1(x)))

        if self.feature_transform:
            trans_feat = self.fstn(x)
            x = x.transpose(2,1)
            x = torch.bmm(x, trans_feat)
            x = x.transpose(2,1)
        else:
            trans_feat = None

        pointfeat = x
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.bn3(self.conv3(x))
        x = torch.max(x, 2, keepdim=True)[0]
        x = x.view(-1, 1024)
        if self.global_feat:
            x = x.view(-1, 1024, 1)
            return x, pointfeat, trans, trans_feat
        else:
            x = x.view(-1, 1024, 1).repeat(1, 1, n_pts)
            # return torch.cat([x, pointfeat], 1), trans, trans_feat
            return x, pointfeat, trans, trans_feat

class PointNetfeat4(nn.Module):
    def __init__(self, d=5,global_feat = True, feature_transform = False):
        super(PointNetfeat4, self).__init__()
        # self.stn = STN3d()
        self.stn=STNkd(k=d)
        # self.conv1 = torch.nn.Conv1d(3, 64, 1)
        self.conv1 = torch.nn.Conv1d(d, 64, 1)
        self.conv2 = torch.nn.Conv1d(64, 128, 1)
        self.conv3 = torch.nn.Conv1d(128, 1024, 1)
        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(1024)
        self.global_feat = global_feat
        self.feature_transform = feature_transform
        if self.feature_transform:
            self.fstn = STNkd(k=64)

    def forward(self, x):
        n_pts = x.size()[2]
        trans = self.stn(x)
        x = x.transpose(2, 1)
        x = torch.bmm(x, trans)
        x = x.transpose(2, 1)
        x = F.relu(self.bn1(self.conv1(x)))

        if self.feature_transform:
            trans_feat = self.fstn(x)
            x = x.transpose(2,1)
            x = torch.bmm(x, trans_feat)
            x = x.transpose(2,1)
        else:
            trans_feat = None

        pointfeat = x
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.bn3(self.conv3(x))
        x = torch.max(x, 2, keepdim=True)[0]
        x = x.view(-1, 1024)
        if self.global_feat:
            x = x.view(-1, 1024, 1)
            return x, pointfeat, trans, trans_feat
        else:
            x = x.view(-1, 1024, 1).repeat(1, 1, n_pts)
            # return torch.cat([x, pointfeat], 1), trans, trans_feat
            return x, pointfeat, trans, trans_feat

class PointNetfeat4p(nn.Module):
    def __init__(self, d=5,global_feat = True, feature_transform = False):
        super(PointNetfeat4p, self).__init__()
        # self.stn = STN3d()
        self.stn=STNkd(k=d)
        # self.conv1 = torch.nn.Conv1d(3, 64, 1)
        self.conv1 = torch.nn.Conv1d(d, 64, 1)
        self.conv2 = torch.nn.Conv1d(64, 128, 1)
        self.conv3 = torch.nn.Conv1d(128, 1024, 1)
        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(1024)
        self.global_feat = global_feat
        self.feature_transform = feature_transform
        if self.feature_transform:
            self.fstn = STNkd(k=64)

    def forward(self, x):
        n_pts = x.size()[2]
        trans = self.stn(x)
        x = x.transpose(2, 1)
        x = torch.bmm(x, trans)
        x = x.transpose(2, 1)
        x = F.relu(self.bn1(self.conv1(x)))

        if self.feature_transform:
            trans_feat = self.fstn(x)
            x = x.transpose(2,1)
            x = torch.bmm(x, trans_feat)
            x = x.transpose(2,1)
        else:
            trans_feat = None

        pointfeat = x
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.bn3(self.conv3(x))
        bmfeat=x
        x = torch.max(x, 2, keepdim=True)[0]
        x = x.view(-1, 1024)
        if self.global_feat:
            x = x.view(-1, 1024, 1)
            return x, pointfeat, bmfeat,trans, trans_feat
        else:
            x = x.view(-1, 1024, 1).repeat(1, 1, n_pts)
            # return torch.cat([x, pointfeat], 1), trans, trans_feat
            return x, pointfeat, trans, trans_feat


class PointNetfeat5(nn.Module):
    def __init__(self, d=6,global_feat = True, feature_transform = False):
        super(PointNetfeat5, self).__init__()
        self.conv0 = torch.nn.Conv1d(d, 3, 1)
        self.stn = STN3d()
        # self.stn=STNkd(k=d)
        self.conv1 = torch.nn.Conv1d(3, 64, 1)
        # self.conv1 = torch.nn.Conv1d(d, 64, 1)
        self.conv2 = torch.nn.Conv1d(64, 128, 1)
        self.conv3 = torch.nn.Conv1d(128, 1024, 1)
        self.bn0 = nn.BatchNorm1d(3)
        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(1024)
        self.global_feat = global_feat
        self.feature_transform = feature_transform
        if self.feature_transform:
            self.fstn = STNkd(k=64)

    def forward(self, x):
        x = F.relu(self.bn0(self.conv0(x)))
        n_pts = x.size()[2]
        trans = self.stn(x)
        x = x.transpose(2, 1)
        x = torch.bmm(x, trans)
        x = x.transpose(2, 1)
        # x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))

        if self.feature_transform:
            trans_feat = self.fstn(x)
            x = x.transpose(2,1)
            x = torch.bmm(x, trans_feat)
            x = x.transpose(2,1)
        else:
            trans_feat = None

        pointfeat = x
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.bn3(self.conv3(x))
        x = torch.max(x, 2, keepdim=True)[0]
        x = x.view(-1, 1024)
        if self.global_feat:
            x = x.view(-1, 1024, 1)
            return x, pointfeat, trans, trans_feat
        else:
            x = x.view(-1, 1024, 1).repeat(1, 1, n_pts)
            # return torch.cat([x, pointfeat], 1), trans, trans_feat
            return x, pointfeat, trans, trans_feat

class PointNetfeat6(nn.Module):
    def __init__(self, d=6,global_feat = True, feature_transform = False):
        super(PointNetfeat6, self).__init__()
        self.conv0 = torch.nn.Conv1d(d, 3, 1)
        self.stn = STN3d()
        # self.stn=STNkd(k=d)
        self.conv1 = torch.nn.Conv1d(3, 64, 1)
        # self.conv1 = torch.nn.Conv1d(d, 64, 1)
        self.conv2 = torch.nn.Conv1d(64, 128, 1)
        self.conv3 = torch.nn.Conv1d(128, 512, 1)
        self.bn0 = nn.BatchNorm1d(3)
        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(512)
        self.global_feat = global_feat
        self.feature_transform = feature_transform
        if self.feature_transform:
            self.fstn = STNkd(k=64)

    def forward(self, x):
        x = F.relu(self.bn0(self.conv0(x)))
        n_pts = x.size()[2]
        trans = self.stn(x)
        x = x.transpose(2, 1)
        x = torch.bmm(x, trans)
        x = x.transpose(2, 1)
        # x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))

        if self.feature_transform:
            trans_feat = self.fstn(x)
            x = x.transpose(2,1)
            x = torch.bmm(x, trans_feat)
            x = x.transpose(2,1)
        else:
            trans_feat = None

        pointfeat = x
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.bn3(self.conv3(x))
        x = torch.max(x, 2, keepdim=True)[0]
        x = x.view(-1, 512)
        if self.global_feat:
            x = x.view(-1, 512, 1)
            return x, pointfeat, trans, trans_feat
        else:
            x = x.view(-1, 512, 1).repeat(1, 1, n_pts)
            # return torch.cat([x, pointfeat], 1), trans, trans_feat
            return x, pointfeat, trans, trans_feat

class PointNetfeat7(nn.Module):
    def __init__(self, d=5,global_feat = True, feature_transform = False):
        super(PointNetfeat7, self).__init__()
        # self.stn = STN3d()
        self.stn=STNkd(k=d)
        # self.conv1 = torch.nn.Conv1d(3, 64, 1)
        self.conv1 = torch.nn.Conv1d(d, 64, 1)
        self.conv2 = torch.nn.Conv1d(64, 128, 1)
        self.conv3 = torch.nn.Conv1d(128, 256, 1)
        self.conv4 = torch.nn.Conv1d(256, 1024, 1)
        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(256)
        self.bn4 = nn.BatchNorm1d(1024)
        self.global_feat = global_feat
        self.feature_transform = feature_transform
        if self.feature_transform:
            self.fstn = STNkd(k=64)

    def forward(self, x):
        n_pts = x.size()[2]
        trans = self.stn(x)
        x = x.transpose(2, 1)
        x = torch.bmm(x, trans)
        x = x.transpose(2, 1)
        x = F.relu(self.bn1(self.conv1(x)))

        if self.feature_transform:
            trans_feat = self.fstn(x)
            x = x.transpose(2,1)
            x = torch.bmm(x, trans_feat)
            x = x.transpose(2,1)
        else:
            trans_feat = None

        pointfeat = x
        x = F.relu(self.bn2(self.conv2(x)))
        pointfeat1 = x
        x = F.relu(self.bn3(self.conv3(x)))
        pointfeat2 = x
        x = self.bn4(self.conv4(x))
        x = torch.max(x, 2, keepdim=True)[0]
        x = x.view(-1, 1024)
        if self.global_feat:
            x = x.view(-1, 1024, 1)
            return x, pointfeat,pointfeat1,pointfeat2, trans, trans_feat
        else:
            x = x.view(-1, 1024, 1).repeat(1, 1, n_pts)
            # return torch.cat([x, pointfeat], 1), trans, trans_feat
            return x, pointfeat,pointfeat1,pointfeat2, trans, trans_feat

class MiniPointNetfeat0(nn.Module):
    def __init__(self, d=3):
        super(MiniPointNetfeat0, self).__init__()
        self.stn = STN3d()
        # self.stn=STNkd(k=d)
        # self.conv1 = torch.nn.Conv1d(3, 64, 1)
        self.conv1 = torch.nn.Conv1d(d, 64, 1)
        self.conv2 = torch.nn.Conv1d(64, 128, 1)
        self.conv3 = torch.nn.Conv1d(128, 1024, 1)
        # self.conv3 = torch.nn.Conv1d(128, 512, 1)
        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(1024)
        # self.bn3 = nn.BatchNorm1d(512)
        # self.global_feat = global_feat
        # self.feature_transform = feature_transform
        # if self.feature_transform:
        #     self.fstn = STNkd(k=64)

    def forward(self, x):
        n_pts = x.size()[2]
        trans = self.stn(x)
        x = x.transpose(2, 1)
        x = torch.bmm(x, trans)
        x = x.transpose(2, 1)
        x = F.relu(self.bn1(self.conv1(x)))

        # if self.feature_transform:
        #     trans_feat = self.fstn(x)
        #     x = x.transpose(2,1)
        #     x = torch.bmm(x, trans_feat)
        #     x = x.transpose(2,1)
        # else:
        #     trans_feat = None

        # pointfeat = x
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.bn3(self.conv3(x))
        return x
        # x=x*segatt
        # x = torch.max(x, 2, keepdim=True)[0]
        # x = x.view(-1, 1024)
        # if self.global_feat:
        #     x = x.view(-1, 1024, 1)
        #     return x, pointfeat, trans, trans_feat
        # else:
        #     x = x.view(-1, 1024, 1).repeat(1, 1, n_pts)
        #     # return torch.cat([x, pointfeat], 1), trans, trans_feat
        #     return x, pointfeat, trans, trans_feat

class PointNetCls(nn.Module):
    def __init__(self, k=2, feature_transform=False):
        super(PointNetCls, self).__init__()
        self.feature_transform = feature_transform
        self.feat = PointNetfeat(global_feat=True, feature_transform=feature_transform)
        self.fc1 = nn.Linear(1024, 512)
        self.fc2 = nn.Linear(512, 256)
        self.fc3 = nn.Linear(256, k)
        self.dropout = nn.Dropout(p=0.3)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.relu = nn.ReLU()

    def forward(self, x):
        x, trans, trans_feat = self.feat(x)
        x = F.relu(self.bn1(self.fc1(x)))
        x = F.relu(self.bn2(self.dropout(self.fc2(x))))
        x = self.fc3(x)
        return F.log_softmax(x, dim=1), trans, trans_feat


class PointNetDenseCls(nn.Module):
    def __init__(self, k = 2, feature_transform=False):
        super(PointNetDenseCls, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        # self.feat = PointNetfeat(global_feat=True, feature_transform=feature_transform)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        # self.conv4 = torch.nn.Conv1d(128, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(x1.size())
        # print(xf.size())
        x1a=torch.cat([x1pf, xf1], 1)
        x2a = torch.cat([x2pf, xf2], 1)
        x=torch.cat((x1a,x2a),0)
        x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        x = F.log_softmax(x.view(-1,self.k), dim=-1)
        x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        # x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        # x = x.view(batchsize, n_pts * 2, 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)
        return x,trans1, trans_feat1

class PointNetDenseCls2(nn.Module):
    def __init__(self, k = 2, feature_transform=False):
        super(PointNetDenseCls2, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        # self.feat = PointNetfeat(global_feat=True, feature_transform=feature_transform)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv4 = torch.nn.Conv1d(128, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(x1.size())
        # print(xf.size())
        x1a=torch.cat([x1pf, xf1], 1)
        x2a = torch.cat([x2pf, xf2], 1)
        x=torch.cat((x1a,x2a),0)
        x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        # x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, n_pts * 2, 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)
        return x,trans1, trans_feat1

class PointNetDenseCls3(nn.Module):
    def __init__(self, k = 2, feature_transform=False):
        super(PointNetDenseCls3, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        # self.feat = PointNetfeat(global_feat=True, feature_transform=feature_transform)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv4 = torch.nn.Conv1d(128, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(x1.size())
        # print(xf.size())
        x1a=torch.cat([x1pf, xf1], 1)
        x2a = torch.cat([x2pf, xf2], 1)
        x=torch.cat((x1a,x2a),0)
        x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, n_pts * 2, 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)
        return x,trans1, trans_feat1

class PointNetDenseCls4(nn.Module):
    def __init__(self, k = 2, feature_transform=False):
        super(PointNetDenseCls4, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat(global_feat=True, feature_transform=feature_transform)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv4 = torch.nn.Conv1d(128, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1gf.size())
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)
        return x,trans1, trans_feat1

class PointNetDenseCls5(nn.Module):
    def __init__(self, k = 2, feature_transform=False):
        super(PointNetDenseCls5, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat2(global_feat=True, feature_transform=feature_transform)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv4 = torch.nn.Conv1d(128, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.dropout = nn.Dropout(p=0.3)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1gf.size())
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)
        return x,trans1, trans_feat1

class PointNetDenseCls6(nn.Module):
    def __init__(self, k = 2, inputd=4,feature_transform=False):
        super(PointNetDenseCls6, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat3(d=inputd,global_feat=True, feature_transform=feature_transform)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv4 = torch.nn.Conv1d(128, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1gf.size())
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)
        return x,trans1, trans_feat1

class PointNetDenseCls7(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0):
        super(PointNetDenseCls7, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat2(global_feat=True, feature_transform=feature_transform)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv4 = torch.nn.Conv1d(128, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1gf.size())
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)
        return x,trans1, trans_feat1

class PointNetDenseCls8(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0):
        super(PointNetDenseCls8, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat3(global_feat=True, feature_transform=feature_transform)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv4 = torch.nn.Conv1d(128, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1gf.size())
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)

        return x,trans1, trans_feat1

class PointNetDenseCls9(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0):
        super(PointNetDenseCls9, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat2(global_feat=True, feature_transform=feature_transform)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv4 = torch.nn.Conv1d(128, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        # self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1gf.size())
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        # x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)
        return x,trans1, trans_feat1

class PointNetDenseCls10(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=6):
        super(PointNetDenseCls10, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat4(global_feat=True, feature_transform=feature_transform,d=id)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv4 = torch.nn.Conv1d(128, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1gf.size())
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)

        return x,trans1, trans_feat1

class PointNetDenseCls11(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=6):
        super(PointNetDenseCls11, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat4(global_feat=True, feature_transform=feature_transform,d=id)
        # self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv4 = torch.nn.Conv1d(128, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1.size())
        # print(x1pf.size())
        x1pf=torch.cat([x1pf,x1[:,3:,:]],1)
        x2pf = torch.cat([x2pf, x2[:, 3:, :]],1)
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)

        return x,trans1, trans_feat1

class PointNetDenseCls12(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=5):
        super(PointNetDenseCls12, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat4(global_feat=True, feature_transform=feature_transform,d=id)
        # self.minifeat=MiniPointNetfeat0(global_feat=True, feature_transform=feature_transform,d=id)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        # self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        self.conv4 = torch.nn.Conv1d(128, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128+id-3, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv5 = torch.nn.Conv1d(64, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.bn4 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1.size())
        # print(x1pf.size())
        # x1pf=torch.cat([x1pf,x1[:,3:,:]],1)
        # x2pf = torch.cat([x2pf, x2[:, 3:, :]],1)
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        # x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        # adx=torch.cat((x1[:,3:,:],x2[:,3:,:]),2)
        # x = torch.cat([x, adx], 1)
        # x = F.relu(self.bn4(self.dropout(self.conv4(x))))
        x = F.relu(self.bn4(self.conv4(x)))
        x = self.conv5(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # x1att=x[:,0:n_pts,:]
        # x2att = x[:,n_pts:, :]
        # x1geo=x1geo*x1att
        # x2geo=x2geo*x2att
        # x1geo = torch.max(x1geo, 2, keepdim=True)[0]
        # x1geo = x1geo.view(-1, 1024)
        # x2geo = torch.max(x2geo, 2, keepdim=True)[0]
        # x2geo = x2geo.view(-1, 1024)

        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)

        return x, trans_feat1, trans_feat2

class PointNetDenseCls13(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=6):
        super(PointNetDenseCls13, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat5(global_feat=True, feature_transform=feature_transform,d=id)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        # self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        self.conv4 = torch.nn.Conv1d(128+id-3, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv5 = torch.nn.Conv1d(64, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.bn4 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1.size())
        # print(x1pf.size())
        # x1pf=torch.cat([x1pf,x1[:,3:,:]],1)
        # x2pf = torch.cat([x2pf, x2[:, 3:, :]],1)
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        # x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        adx=torch.cat((x1[:,3:,:],x2[:,3:,:]),2)
        x = torch.cat([x, adx], 1)
        x = F.relu(self.bn4(self.dropout(self.conv4(x))))
        x = self.conv5(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)

        return x,trans1, trans_feat1

class PointNetDenseCls14(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=6):
        super(PointNetDenseCls14, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat6(global_feat=True, feature_transform=feature_transform,d=id)
        self.conv0 = torch.nn.Conv1d(1024+64, 512, 1)
        # self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.conv1 = torch.nn.Conv1d(512, 256, 1)
        self.conv2 = torch.nn.Conv1d(256, 128, 1)
        self.conv3 = torch.nn.Conv1d(128, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv4 = torch.nn.Conv1d(64, 1, 1)
        self.bn0 = nn.BatchNorm1d(512)
        self.bn1 = nn.BatchNorm1d(256)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1.size())
        # print(x1pf.size())
        # x1pf=torch.cat([x1pf,x1[:,3:,:]],1)
        # x2pf = torch.cat([x2pf, x2[:, 3:, :]],1)
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        # x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        # x = F.relu(self.bn4(self.dropout(self.conv4(x))))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)

        return x,trans1, trans_feat1

class PointNetDenseCls15(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=6):
        super(PointNetDenseCls15, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat6(global_feat=True, feature_transform=feature_transform,d=id)
        self.attn1 = nn.Linear(512 * 2, 512)
        self.attn2 = nn.Linear(512 * 2, 512)
        # self.attn_combine = nn.Linear(self.hidden_size * 2, self.hidden_size)
        # self.conv0 = torch.nn.Conv1d(1024+64, 512, 1)
        self.conv0 = torch.nn.Conv1d(512+64, 256, 1)
        # self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.conv1 = torch.nn.Conv1d(256, 128, 1)
        self.conv2 = torch.nn.Conv1d(128, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv3 = torch.nn.Conv1d(64, 1, 1)
        self.bn0 = nn.BatchNorm1d(256)
        self.bn1 = nn.BatchNorm1d(128)
        self.bn2 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        print(x1gf.size())
        x1gf=x1gf.view(-1, 512)
        x2gf = x2gf.view(-1, 512)
        print(x1gf.size())
        attn_weights1 = F.softmax(self.attn1(torch.cat((x1gf,x2gf), 1)), dim=1)
        attn_applied1 = torch.bmm(attn_weights1.unsqueeze(0),x1gf.unsqueeze(0))

        attn_weights2 = F.softmax(self.attn2(torch.cat((x2gf, x1gf), 1)), dim=1)
        attn_applied2 = torch.bmm(attn_weights2.unsqueeze(0), x2gf.unsqueeze(0))
        # print(x1.size())
        # print(x1pf.size())
        # x1pf=torch.cat([x1pf,x1[:,3:,:]],1)
        # x2pf = torch.cat([x2pf, x2[:, 3:, :]],1)
        # print(x2gf.size())
        # xf1=torch.cat([x1gf, x2gf], 1)
        # xf2 = torch.cat([x2gf, x1gf], 1)
        xf1 = attn_applied1
        xf2 = attn_applied2
        xf1 = xf1.view(-1, 512, 1)
        xf2 = xf2.view(-1, 512, 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        # x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        # x = F.relu(self.bn4(self.dropout(self.conv4(x))))
        x = self.conv4(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)

        return x,trans1, trans_feat1

class PointNetDenseCls16(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=5):
        super(PointNetDenseCls16, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat4(global_feat=True, feature_transform=feature_transform,d=id)
        # self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv0 = torch.nn.Conv1d(2048, 1024, 1)
        # self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.att=torch.nn.Softmax(dim=1)
        self.conv1 = torch.nn.Conv1d(1024+64, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        self.conv4 = torch.nn.Conv1d(128, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128+id-3, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv5 = torch.nn.Conv1d(64, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.bn4 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1.size())
        # print(x1pf.size())
        # x1pf=torch.cat([x1pf,x1[:,3:,:]],1)
        # x2pf = torch.cat([x2pf, x2[:, 3:, :]],1)
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)

        attx1 = F.relu(self.bn0(self.dropout(self.conv0(xf1))))
        attpara1 = self.att(attx1)

        attx2 = F.relu(self.bn0(self.dropout(self.conv0(xf2))))
        attpara2 = self.att(attx2)

        xf1=x1gf*attpara1
        xf2=x2gf*attpara2

        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])

        x1a=torch.cat([x1pf, xf1], 1)
        x2a = torch.cat([x2pf, xf2], 1)

        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        # attx = F.relu(self.bn0(self.dropout(self.conv0(x))))
        # x = F.relu(self.bn0(self.conv0(x)))
        # attpara=self.att(attx)
        # print(attpara.size())
        # x =torch.cat([x[:,0:64,:],attpara*x[:,64:1088,:]],1)
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        # adx=torch.cat((x1[:,3:,:],x2[:,3:,:]),2)
        # x = torch.cat([x, adx], 1)
        # x = F.relu(self.bn4(self.dropout(self.conv4(x))))
        x = F.relu(self.bn4(self.conv4(x)))
        x = self.conv5(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)

        return x,trans1, trans_feat1

class PointNetDenseCls17(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=5):
        super(PointNetDenseCls17, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat4(global_feat=True, feature_transform=feature_transform,d=id)
        # self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv0 = torch.nn.Conv1d(2048, 1024, 1)
        self.conv01 = torch.nn.Conv1d(1024+64, 1024, 1)
        # self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.att=torch.nn.Softmax(dim=1)
        self.conv1 = torch.nn.Conv1d(1024+64, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        self.conv4 = torch.nn.Conv1d(128, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128+id-3, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv5 = torch.nn.Conv1d(64, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.bn4 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1.size())
        # print(x1pf.size())
        # x1pf=torch.cat([x1pf,x1[:,3:,:]],1)
        # x2pf = torch.cat([x2pf, x2[:, 3:, :]],1)
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)

        attx1 = F.relu(self.bn0(self.dropout(self.conv0(xf1))))
        attpara01 = self.att(attx1)

        attx2 = F.relu(self.bn0(self.dropout(self.conv0(xf2))))
        attpara02 = self.att(attx2)

        # xf1=x1gf*attpara1
        # xf2=x2gf*attpara2

        xf1 = x1gf.repeat(1, 1, x1pf.size()[2])
        xf2 = x2gf.repeat(1, 1, x2pf.size()[2])

        x1a = torch.cat([x1pf, xf1], 1)
        x2a = torch.cat([x2pf, xf2], 1)

        attx1 = F.relu(self.bn0(self.dropout(self.conv01(x1a))))
        attpara11 = self.att(attx1)

        attx2 = F.relu(self.bn0(self.dropout(self.conv01(x2a))))
        attpara12 = self.att(attx2)

        xf1=x1gf*attpara01*attpara11
        xf2=x2gf*attpara02*attpara12

        # print(xf1.size())
        #
        # xf1=xf1.repeat(1,1,x1pf.size()[2])
        # xf2 = xf2.repeat(1, 1, x2pf.size()[2])

        x1a=torch.cat([x1pf, xf1], 1)
        x2a = torch.cat([x2pf, xf2], 1)

        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        # attx = F.relu(self.bn0(self.dropout(self.conv0(x))))
        # x = F.relu(self.bn0(self.conv0(x)))
        # attpara=self.att(attx)
        # print(attpara.size())
        # x =torch.cat([x[:,0:64,:],attpara*x[:,64:1088,:]],1)
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        # adx=torch.cat((x1[:,3:,:],x2[:,3:,:]),2)
        # x = torch.cat([x, adx], 1)
        # x = F.relu(self.bn4(self.dropout(self.conv4(x))))
        x = F.relu(self.bn4(self.conv4(x)))
        x = self.conv5(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)

        return x,trans1, trans_feat1


class PointNetDenseCls18(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=5):
        super(PointNetDenseCls18, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat7(global_feat=True, feature_transform=feature_transform,d=id)
        # self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        self.conv0 = torch.nn.Conv1d(2048+64+128+256, 1024, 1)
        # self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        self.conv4 = torch.nn.Conv1d(128, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128+id-3, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv5 = torch.nn.Conv1d(64, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.bn4 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf0,x1pf1,x1pf2, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf0,x2pf1,x2pf2, trans2, trans_feat2 = self.feat(x2)
        x1pf=torch.cat((x1pf0,x1pf1,x1pf2),1)
        x2pf = torch.cat((x2pf0, x2pf1, x2pf2), 1)
        # print(x1.size())
        # print(x1pf.size())
        # x1pf=torch.cat([x1pf,x1[:,3:,:]],1)
        # x2pf = torch.cat([x2pf, x2[:, 3:, :]],1)
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        # x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        # adx=torch.cat((x1[:,3:,:],x2[:,3:,:]),2)
        # x = torch.cat([x, adx], 1)
        # x = F.relu(self.bn4(self.dropout(self.conv4(x))))
        x = F.relu(self.bn4(self.conv4(x)))
        x = self.conv5(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)

        return x, trans_feat1, trans_feat2

class PointNetDenseCls19(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=5):
        super(PointNetDenseCls19, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat7(global_feat=True, feature_transform=feature_transform,d=id)
        # self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        # self.conv0 = torch.nn.Conv1d(2048+64+128+256, 1024, 1)
        self.conv0 = torch.nn.Conv1d(2048, 1024, 1)
        self.conv01 = torch.nn.Conv1d(1024 + 64+128+256, 1024, 1)
        # self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.att = torch.nn.Softmax(dim=1)
        # self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024 + 64+128+256, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        self.conv4 = torch.nn.Conv1d(128, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128+id-3, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv5 = torch.nn.Conv1d(64, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.bn4 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf0,x1pf1,x1pf2, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf0,x2pf1,x2pf2, trans2, trans_feat2 = self.feat(x2)
        x1pf=torch.cat((x1pf0,x1pf1,x1pf2),1)
        x2pf = torch.cat((x2pf0, x2pf1, x2pf2), 1)
        # print(x1.size())
        # print(x1pf.size())
        # x1pf=torch.cat([x1pf,x1[:,3:,:]],1)
        # x2pf = torch.cat([x2pf, x2[:, 3:, :]],1)
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)

        attx1 = F.relu(self.bn0(self.dropout(self.conv0(xf1))))
        attpara01 = self.att(attx1)

        attx2 = F.relu(self.bn0(self.dropout(self.conv0(xf2))))
        attpara02 = self.att(attx2)

        xf1 = x1gf.repeat(1, 1, x1pf.size()[2])
        xf2 = x2gf.repeat(1, 1, x2pf.size()[2])

        x1a = torch.cat([x1pf, xf1], 1)
        x2a = torch.cat([x2pf, xf2], 1)

        attx1 = F.relu(self.bn0(self.dropout(self.conv01(x1a))))
        attpara11 = self.att(attx1)

        attx2 = F.relu(self.bn0(self.dropout(self.conv01(x2a))))
        attpara12 = self.att(attx2)

        xf1 = x1gf * attpara01 * attpara11
        xf2 = x2gf * attpara02 * attpara12
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())

        x1a = torch.cat([x1pf, xf1], 1)
        x2a = torch.cat([x2pf, xf2], 1)

        x = torch.cat((x1a, x2a), 2)
        # xf1=xf1.repeat(1,1,x1pf.size()[2])
        # xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        # x1a=torch.cat([x1pf, xf1], 1)
        # # print(x1a.size())
        # x2a = torch.cat([x2pf, xf2], 1)
        # # print(x2a.size())
        # x=torch.cat((x1a,x2a),2)
        # print(x.size())
        # x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        # x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.dropout(self.conv1(x))))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        # adx=torch.cat((x1[:,3:,:],x2[:,3:,:]),2)
        # x = torch.cat([x, adx], 1)
        # x = F.relu(self.bn4(self.dropout(self.conv4(x))))
        x = F.relu(self.bn4(self.conv4(x)))
        x = self.conv5(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)

        return x, trans_feat1, trans_feat2

class PointNetDenseCls20(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=5):
        super(PointNetDenseCls20, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat4(global_feat=True, feature_transform=feature_transform,d=id)
        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        # self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        self.conv4 = torch.nn.Conv1d(128, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128+id-3, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv5 = torch.nn.Conv1d(64, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.bn4 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        # print(x1.size())
        # print(x1pf.size())
        # x1pf=torch.cat([x1pf,x1[:,3:,:]],1)
        # x2pf = torch.cat([x2pf, x2[:, 3:, :]],1)
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        # x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        # adx=torch.cat((x1[:,3:,:],x2[:,3:,:]),2)
        # x = torch.cat([x, adx], 1)
        x = F.relu(self.bn4(self.dropout(self.conv4(x))))
        # x = F.relu(self.bn4(self.conv4(x)))
        x = self.conv5(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, x1.size()[2]+x2.size()[2], 1)
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)

        return x, trans_feat1, trans_feat2

class PointNetDenseCls21(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=5):
        super(PointNetDenseCls21, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat4(global_feat=True, feature_transform=feature_transform,d=id)
        self.minifeat=MiniPointNetfeat0(d=3)

        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        # self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        self.conv4 = torch.nn.Conv1d(128, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128+id-3, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv5 = torch.nn.Conv1d(64, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.bn4 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, trans2, trans_feat2 = self.feat(x2)
        x1geo=self.minifeat(x1[:,0:3,:])
        x2geo=self.minifeat(x2[:,0:3,:])
        # print(x1.size())
        # print(x1pf.size())
        # x1pf=torch.cat([x1pf,x1[:,3:,:]],1)
        # x2pf = torch.cat([x2pf, x2[:, 3:, :]],1)
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        # x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        # adx=torch.cat((x1[:,3:,:],x2[:,3:,:]),2)
        # x = torch.cat([x, adx], 1)
        # x = F.relu(self.bn4(self.dropout(self.conv4(x))))
        x = F.relu(self.bn4(self.conv4(x)))
        x = self.conv5(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, 1,x1.size()[2]+x2.size()[2])
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)
        # x1att = torch.sigmoid(x[:,0:n_pts,:])
        # x2att = torch.sigmoid(x[:, n_pts:, :])
        x1att = torch.sigmoid(x[:, :,0:n_pts])
        x2att = torch.sigmoid(x[:, :,n_pts:])
        # print(x1att.size())
        # print(x1geo.size())
        x1geo = x1geo * x1att
        x2geo = x2geo * x2att
        x1geo = torch.max(x1geo, 2, keepdim=True)[0]
        x1geo = x1geo.view(-1, 1024)
        x2geo = torch.max(x2geo, 2, keepdim=True)[0]
        x2geo = x2geo.view(-1, 1024)
        # print(x2geo.size())
        x = x.view(batchsize, x1.size()[2] + x2.size()[2], 1)

        return x, x1geo,x2geo,trans_feat1, trans_feat2

class PointNetDenseCls23(nn.Module):
    def __init__(self, k = 2, feature_transform=False,pdrop=0.0,id=5):
        super(PointNetDenseCls23, self).__init__()
        self.k = k
        self.feature_transform=feature_transform
        # self.feat = PointNetfeat(global_feat=False, feature_transform=feature_transform)
        self.feat = PointNetfeat4p(global_feat=True, feature_transform=feature_transform,d=id)
        self.minifeat=MiniPointNetfeat0(d=3)

        self.conv0 = torch.nn.Conv1d(2112, 1024, 1)
        # self.conv0 = torch.nn.Conv1d(2112+id-3, 1024, 1)
        self.conv1 = torch.nn.Conv1d(1024, 512, 1)
        self.conv2 = torch.nn.Conv1d(512, 256, 1)
        self.conv3 = torch.nn.Conv1d(256, 128, 1)
        self.conv4 = torch.nn.Conv1d(128, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128+id-3, 64, 1)
        # self.conv4 = torch.nn.Conv1d(128, self.k, 1)
        self.conv5 = torch.nn.Conv1d(64, 1, 1)
        self.bn0 = nn.BatchNorm1d(1024)
        self.bn1 = nn.BatchNorm1d(512)
        self.bn2 = nn.BatchNorm1d(256)
        self.bn3 = nn.BatchNorm1d(128)
        self.bn4 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(p=pdrop)
        # self.ls=nn.LogSigmoid()
        # self.ls = torch.sigmoid()

    def forward(self, x1,x2):
        # batchsize = x.size()[0]
        batchsize = x1.size()[0]
        # n_pts = x.size()[2]
        n_pts = x1.size()[2]
        x1gf,x1pf, x1geo,trans1, trans_feat1 = self.feat(x1)
        x2gf,x2pf, x2geo,trans2, trans_feat2 = self.feat(x2)
        # x1geo=self.minifeat(x1[:,0:3,:])
        # x2geo=self.minifeat(x2[:,0:3,:])
        # print(x1.size())
        # print(x1pf.size())
        # x1pf=torch.cat([x1pf,x1[:,3:,:]],1)
        # x2pf = torch.cat([x2pf, x2[:, 3:, :]],1)
        # print(x2gf.size())
        xf1=torch.cat([x1gf, x2gf], 1)
        xf2 = torch.cat([x2gf, x1gf], 1)
        # xf = xf.view(-1, 1024, 1).repeat(1, 1, n_pts)
        # print(xf1.size())
        # print(xf2.size())
        xf1=xf1.repeat(1,1,x1pf.size()[2])
        xf2 = xf2.repeat(1, 1, x2pf.size()[2])
        x1a=torch.cat([x1pf, xf1], 1)
        # print(x1a.size())
        x2a = torch.cat([x2pf, xf2], 1)
        # print(x2a.size())
        x=torch.cat((x1a,x2a),2)
        # print(x.size())
        x = F.relu(self.bn0(self.dropout(self.conv0(x))))
        # x = F.relu(self.bn0(self.conv0(x)))
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        # adx=torch.cat((x1[:,3:,:],x2[:,3:,:]),2)
        # x = torch.cat([x, adx], 1)
        # x = F.relu(self.bn4(self.dropout(self.conv4(x))))
        x = F.relu(self.bn4(self.conv4(x)))
        x = self.conv5(x)
        x = x.transpose(2,1).contiguous()
        # x = F.log_softmax(x.view(-1,self.k), dim=-1)
        # x = x.view(batchsize, n_pts*2, self.k)
        # self.k=1
        x=x.view(-1, 1)
        # x = nn.LogSigmoid(x)
        # x = self.ls(x.view(-1, 1))
        # x=torch.sigmoid(x.view(-1, 1))
        x = x.view(batchsize, 1,x1.size()[2]+x2.size()[2])
        # return x, torch.cat((trans1,trans2),0), torch.cat((trans_feat1,trans_feat2),0)
        # x1att = torch.sigmoid(x[:,0:n_pts,:])
        # x2att = torch.sigmoid(x[:, n_pts:, :])
        x1att = torch.sigmoid(x[:, :,0:n_pts])
        x2att = torch.sigmoid(x[:, :,n_pts:])
        # print(x1att.size())
        # print(x1geo.size())
        x1geo = x1geo * x1att
        x2geo = x2geo * x2att
        x1geo = torch.max(x1geo, 2, keepdim=True)[0]
        x1geo = x1geo.view(-1, 1024)
        x2geo = torch.max(x2geo, 2, keepdim=True)[0]
        x2geo = x2geo.view(-1, 1024)
        # print(x2geo.size())
        x = x.view(batchsize, x1.size()[2] + x2.size()[2], 1)

        return x, x1geo,x2geo,trans_feat1, trans_feat2

def feature_transform_regularizer(trans):
    d = trans.size()[1]
    batchsize = trans.size()[0]
    I = torch.eye(d)[None, :, :]
    if trans.is_cuda:
        I = I.cuda()
    loss = torch.mean(torch.norm(torch.bmm(trans, trans.transpose(2,1)) - I, dim=(1,2)))
    return loss

if __name__ == '__main__':
    sim_data = Variable(torch.rand(32,3,2500))
    trans = STN3d()
    out = trans(sim_data)
    print('stn', out.size())
    print('loss', feature_transform_regularizer(out))

    sim_data_64d = Variable(torch.rand(32, 64, 2500))
    trans = STNkd(k=64)
    out = trans(sim_data_64d)
    print('stn64d', out.size())
    print('loss', feature_transform_regularizer(out))

    pointfeat = PointNetfeat(global_feat=True)
    out, _, _ = pointfeat(sim_data)
    print('global feat', out.size())

    pointfeat = PointNetfeat(global_feat=False)
    out, _, _ = pointfeat(sim_data)
    print('point feat', out.size())

    cls = PointNetCls(k = 5)
    out, _, _ = cls(sim_data)
    print('class', out.size())

    seg = PointNetDenseCls(k = 3)
    out, _, _ = seg(sim_data)
    print('seg', out.size())