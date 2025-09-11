import express from "express";
import * as cvAlignController from "../controllers/cvAlignController.js";

export const cvAlignRouter = express.Router();

// For recruiters: rank all CVs for a job
cvAlignRouter.post('/rank', cvAlignController.rankCVs);

// For job seekers: analyse a CV against a job
cvAlignRouter.post('/analyse', cvAlignController.analyseCV);
