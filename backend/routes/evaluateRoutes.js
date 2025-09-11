import express from 'express';
import { evaluateCV } from '../controllers/evaluateController.js';

const router = express.Router();

// POST /api/evaluate-cv
router.post('/', evaluateCV);

export default router;
